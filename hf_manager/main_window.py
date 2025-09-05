import re
import uuid
import copy
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QListWidget, QTabWidget, QTextEdit, QTreeView,
                               QToolBar, QLabel, QPushButton, QInputDialog, QMessageBox, QMenu, QFileDialog)
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt
from .data_model import DataModel
from .huggingface_api import HuggingFaceAPI
from .widgets.folder_selection_dialog import FolderSelectionDialog
from .widgets.settings_dialog import SettingsDialog
from .widgets.tree_model import TreeModel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HuggingFace Download Manager v1.2")
        self.setGeometry(100, 100, 1200, 800)

        self.data_model = DataModel()
        self.hf_api = HuggingFaceAPI()
        self.current_selection = (None, None) # e.g., ("tag", "Qwen-Image") or ("scheme", "My Scheme")

        self.setup_ui()
        self.load_data_to_ui()

    def on_item_changed(self, item):
        if item.column() == 0: # Only handle changes in the 'Name' column
            new_name = item.text()
            entry_data = item.data(Qt.UserRole)

            if entry_data:
                original_path = entry_data.get("path")
                # If the new name is the same as the original path, we can remove the alias
                if new_name == original_path:
                    if "alias" in entry_data:
                        del entry_data["alias"]
                else:
                    entry_data["alias"] = new_name

                self.statusBar().showMessage(f"'{original_path}' will be renamed to '{new_name}'.", 3000)
                self.generate_script_preview()

    def _populate_tree_view(self, data_source, name):
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels(['Name', 'Repo ID', 'Path'])

        # Ensure all items have a UUID
        for item_data in data_source:
            if "uuid" not in item_data:
                item_data["uuid"] = str(uuid.uuid4())

        items_by_uuid = {item["uuid"]: item for item in data_source}
        qitems_by_uuid = {}
        root = self.tree_model.invisibleRootItem()

        for item_data in data_source:
            name = item_data.get("alias", item_data.get("path", "Unknown"))
            name_item = QStandardItem(name)
            name_item.setEditable(True)
            name_item.setData(item_data, Qt.UserRole)
            repo_id_item = QStandardItem(item_data.get("repo_id", ""))
            path_item = QStandardItem(item_data.get("path", ""))
            repo_id_item.setEditable(False)
            path_item.setEditable(False)
            qitems_by_uuid[item_data["uuid"]] = [name_item, repo_id_item, path_item]

        for item_data in data_source:
            parent_uuid = item_data.get("parent_uuid")
            row = qitems_by_uuid[item_data["uuid"]]
            if parent_uuid and parent_uuid in qitems_by_uuid:
                qitems_by_uuid[parent_uuid][0].appendRow(row)
            else:
                root.appendRow(row)

        self.structured_view.expandAll()
        self.generate_script_preview()

    def on_tag_selected(self, item):
        self.schemes_list.clearSelection()
        tag_name = item.text()
        self.current_selection = ("tag", tag_name)
        tag_data = self.data_model.data["tags"].get(tag_name, [])
        self._populate_tree_view(tag_data, tag_name)

    def on_scheme_selected(self, item):
        self.tags_list.clearSelection()
        scheme_name = item.text()
        self.current_selection = ("scheme", scheme_name)
        scheme_data = self.data_model.data["schemes"].get(scheme_name, [])
        self._populate_tree_view(scheme_data, scheme_name)


    def show_structured_view_context_menu(self, pos):
        menu = QMenu(self)
        new_folder_action = menu.addAction("New Virtual Folder")
        delete_action = menu.addAction("Delete Item")
        menu.addSeparator()

        action = menu.exec(self.structured_view.viewport().mapToGlobal(pos))

        if action == new_folder_action:
            self.create_virtual_folder()
        elif action == delete_action:
            self.delete_structured_item()

    def delete_structured_item(self):
        indexes = self.structured_view.selectionModel().selectedIndexes()
        if not indexes:
            return

        reply = QMessageBox.question(self, "Delete Items", f"Are you sure you want to delete {len(indexes)} item(s)?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.No:
            return

        # Get all uuids to be deleted, including children of deleted folders
        uuids_to_delete = set()
        items_to_process = [self.tree_model.itemFromIndex(index) for index in indexes if index.column() == 0]

        for item in items_to_process:
            q = [item]
            while q:
                current = q.pop(0)
                data = current.data(Qt.UserRole)
                if data and "uuid" in data:
                    uuids_to_delete.add(data["uuid"])
                for i in range(current.rowCount()):
                    q.append(current.child(i, 0))

        selection_type, selection_name = self.current_selection
        if not selection_name: return

        data_key = "tags" if selection_type == "tag" else "schemes"

        # Filter out the items from the data model
        original_data = self.data_model.data[data_key][selection_name]
        self.data_model.data[data_key][selection_name] = [
            item for item in original_data if item.get("uuid") not in uuids_to_delete
        ]

        # Refresh the view
        if selection_type == "tag":
            current_item = self.tags_list.findItems(selection_name, Qt.MatchExactly)[0]
            self.on_tag_selected(current_item)
        else:
            current_item = self.schemes_list.findItems(selection_name, Qt.MatchExactly)[0]
            self.on_scheme_selected(current_item)

        self.statusBar().showMessage(f"Deleted {len(uuids_to_delete)} item(s).", 3000)

    def create_virtual_folder(self):
        folder_name, ok = QInputDialog.getText(self, "Create Virtual Folder", "Enter folder name:")
        if not (ok and folder_name):
            return

        selection_type, selection_name = self.current_selection
        if not selection_name:
            QMessageBox.warning(self, "Warning", "Please select a tag or scheme first.")
            return

        selected_index = self.structured_view.currentIndex()
        parent_item = self.tree_model.itemFromIndex(selected_index)
        parent_data = None

        # Determine the parent for the new folder
        parent_node = self.tree_model.invisibleRootItem()
        parent_uuid = None

        if parent_item:
            parent_data = parent_item.data(Qt.UserRole)
            # If the selected item is a file, create the new folder alongside it
            if parent_data and parent_data.get("type") not in ["virtual_folder", "folder"]:
                parent_item = parent_item.parent()

            if parent_item:
                 parent_data = parent_item.data(Qt.UserRole)
                 parent_node = parent_item
                 parent_uuid = parent_data.get("uuid") if parent_data else None

        new_folder_data = {
            "uuid": str(uuid.uuid4()), "alias": folder_name, "type": "virtual_folder",
            "path": "", "repo_id": "", "parent_uuid": parent_uuid
        }

        data_key = "tags" if selection_type == "tag" else "schemes"
        self.data_model.data[data_key][selection_name].append(new_folder_data)

        name_item = QStandardItem(folder_name)
        name_item.setData(new_folder_data, Qt.UserRole)
        name_item.setEditable(True)

        parent_node.appendRow([name_item, QStandardItem(""), QStandardItem("")])
        self.statusBar().showMessage(f"Created virtual folder '{folder_name}'.", 3000)
        self.generate_script_preview()

    def update_data_from_tree(self):
        selection_type, selection_name = self.current_selection
        if not selection_name:
            return

        data_key = "tags" if selection_type == "tag" else "schemes"
        data_source = self.data_model.data[data_key][selection_name]
        items_by_uuid = {item["uuid"]: item for item in data_source}

        root = self.tree_model.invisibleRootItem()

        # Recursive function to traverse the tree and update parent_uuid
        def traverse(parent_item, parent_uuid):
            for row in range(parent_item.rowCount()):
                child_item = parent_item.child(row, 0)
                child_data = child_item.data(Qt.UserRole)
                if child_data:
                    child_uuid = child_data.get("uuid")
                    if child_uuid in items_by_uuid:
                        items_by_uuid[child_uuid]["parent_uuid"] = parent_uuid

                    if child_item.hasChildren():
                        traverse(child_item, child_uuid)

        traverse(root, None)
        self.statusBar().showMessage("Folder structure updated.", 3000)
        self.generate_script_preview()

    def generate_script_preview(self):
        selection_type, selection_name = self.current_selection
        if not selection_name:
            self.raw_script_view.setPlainText("# Select a tag or scheme to see the script.")
            return

        data_key = "tags" if selection_type == "tag" else "schemes"
        data_source = self.data_model.data[data_key].get(selection_name, [])

        if not data_source:
            self.raw_script_view.setPlainText(f"# No items in {selection_type} '{selection_name}'.")
            return

        items_by_uuid = {item["uuid"]: item for item in data_source}

        def get_full_path(item_uuid):
            path_parts = []
            curr_uuid = item_uuid
            while curr_uuid in items_by_uuid:
                item = items_by_uuid[curr_uuid]
                # Use alias for virtual folders in the path, otherwise keep original name for real folders
                if item.get("type") == "virtual_folder":
                    path_parts.append(item.get("alias", "unnamed_folder"))

                curr_uuid = item.get("parent_uuid")

            return "/".join(reversed(path_parts))

        script_lines = ["#!/bin/bash", "# Auto-generated by HuggingFace Download Manager", ""]
        script_lines.append("set -e") # Exit on error
        script_lines.append("export HF_HUB_ENABLE_HF_TRANSFER=1")
        default_root = self.data_model.data.get("settings", {}).get("root_download_dir", "./downloads")
        script_lines.append(f"ROOT_DIR=${{1:-{default_root}}}")
        script_lines.append("echo \"Downloading files to $ROOT_DIR\"")
        script_lines.append("")

        all_dirs = set()
        download_commands = []
        rename_commands = []

        for item in data_source:
            if item.get("type") == "virtual_folder":
                continue

            local_path = get_full_path(item.get("parent_uuid"))
            all_dirs.add(local_path)

            original_name = item.get("path").split('/')[-1]
            repo_id = item.get("repo_id")

            dl_path = f"$ROOT_DIR/{local_path}" if local_path else "$ROOT_DIR"

            # Command to download
            download_commands.append(f"# Downloading: {item.get('path')}")
            download_commands.append(f"huggingface-cli download {repo_id} {item.get('path')} --repo-type model --local-dir \"{dl_path}\" --local-dir-use-symlinks False")

            # Command to rename if alias exists
            alias = item.get("alias")
            if alias and alias != original_name:
                final_path = f"\"{dl_path}/{alias}\""
                original_path_full = f"\"{dl_path}/{original_name}\""
                rename_commands.append(f"# Renaming: {original_name} -> {alias}")
                rename_commands.append(f"mv {original_path_full} {final_path}")

        # Add mkdir commands
        if all_dirs:
            script_lines.append("# --- Create Directories ---")
            for d in sorted(list(all_dirs)):
                if d: # Avoid creating './'
                    script_lines.append(f"mkdir -p \"$ROOT_DIR/{d}\"")
            script_lines.append("")

        # Add download commands
        script_lines.append("# --- Download Files ---")
        script_lines.extend(download_commands)
        script_lines.append("")

        # Add rename commands
        if rename_commands:
            script_lines.append("# --- Rename Files ---")
            script_lines.extend(rename_commands)
            script_lines.append("")

        script_lines.append("echo \"Download script finished.\"")

        self.raw_script_view.setPlainText("\n".join(script_lines))


    def setup_ui(self):
        # --- Menu Bar ---
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        import_action = QAction("Import JSON", self)
        import_action.triggered.connect(self.import_json)
        file_menu.addAction(import_action)

        export_action = QAction("Export JSON", self)
        export_action.triggered.connect(self.export_json)
        file_menu.addAction(export_action)

        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Toolbar ---
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        save_action = QAction("Save Config", self)
        save_action.triggered.connect(self.save_config)
        toolbar.addAction(save_action)

        gen_script_action = QAction("Generate Script", self)
        gen_script_action.triggered.connect(self.generate_script_file)
        toolbar.addAction(gen_script_action)

        toolbar.addSeparator()

        add_link_action = QAction("Add Link", self)
        add_link_action.triggered.connect(self.add_link_to_selected_tag)
        toolbar.addAction(add_link_action)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

        # --- Main Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Left Panel (Navigation) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # --- Tags Section ---
        tags_header_layout = QHBoxLayout()
        tags_header_layout.addWidget(QLabel("Tags"))
        add_tag_button = QPushButton("+")
        add_tag_button.setFixedSize(24, 24)
        add_tag_button.clicked.connect(self.add_tag)
        remove_tag_button = QPushButton("-")
        remove_tag_button.setFixedSize(24, 24)
        remove_tag_button.clicked.connect(self.delete_tag)
        tags_header_layout.addWidget(add_tag_button)
        tags_header_layout.addWidget(remove_tag_button)
        tags_header_layout.addStretch()
        left_layout.addLayout(tags_header_layout)

        self.tags_list = QListWidget()
        self.tags_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tags_list.customContextMenuRequested.connect(self.show_tags_context_menu)
        self.tags_list.itemDoubleClicked.connect(self.rename_tag)
        self.tags_list.itemClicked.connect(self.on_tag_selected)
        left_layout.addWidget(self.tags_list)

        # --- Schemes Section ---
        schemes_header_layout = QHBoxLayout()
        schemes_header_layout.addWidget(QLabel("Configuration Schemes"))
        add_scheme_button = QPushButton("+")
        add_scheme_button.setFixedSize(24, 24)
        add_scheme_button.clicked.connect(self.add_scheme)
        remove_scheme_button = QPushButton("-")
        remove_scheme_button.setFixedSize(24, 24)
        remove_scheme_button.clicked.connect(self.delete_scheme)
        schemes_header_layout.addWidget(add_scheme_button)
        schemes_header_layout.addWidget(remove_scheme_button)
        schemes_header_layout.addStretch()
        left_layout.addLayout(schemes_header_layout)
        self.schemes_list = QListWidget()
        self.schemes_list.itemClicked.connect(self.on_scheme_selected)
        self.schemes_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.schemes_list.customContextMenuRequested.connect(self.show_schemes_context_menu)
        self.schemes_list.itemDoubleClicked.connect(self.rename_scheme)
        self.schemes_list.setAcceptDrops(True)
        self.schemes_list.dragEnterEvent = self.scheme_drag_enter_event
        self.schemes_list.dropEvent = self.scheme_drop_event
        left_layout.addWidget(self.schemes_list)

        # --- Right Panel (Content) ---
        right_panel = QTabWidget()

        self.structured_view = QTreeView()
        self.tree_model = TreeModel()
        self.tree_model.data_changed_callback = self.update_data_from_tree
        self.structured_view.setModel(self.tree_model)
        self.structured_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.structured_view.customContextMenuRequested.connect(self.show_structured_view_context_menu)
        self.structured_view.setDragDropMode(QTreeView.InternalMove)
        self.structured_view.setSelectionMode(QTreeView.ExtendedSelection)
        self.tree_model.itemChanged.connect(self.on_item_changed)

        self.raw_script_view = QTextEdit()
        self.raw_script_view.setReadOnly(True)
        self.raw_script_view.setFontFamily("Courier")
        right_panel.addTab(self.structured_view, "Structured View")
        right_panel.addTab(self.raw_script_view, "Raw Script View")

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 3)

        # --- Status Bar ---
        self.statusBar().showMessage("Ready.")

    def load_data_to_ui(self):
        self.tags_list.clear()
        self.schemes_list.clear()

        tags = self.data_model.get_tags()
        self.tags_list.addItems(tags.keys())

        schemes = self.data_model.get_schemes()
        self.schemes_list.addItems(schemes.keys())

        if self.tags_list.count() > 0:
            self.tags_list.setCurrentRow(0)
            self.on_tag_selected(self.tags_list.item(0))

    def save_config(self):
        self.data_model.save()
        self.statusBar().showMessage("Configuration saved successfully.", 3000)

    def show_tags_context_menu(self, pos):
        item = self.tags_list.itemAt(pos)
        if not item:
            return

        context_menu = QMenu(self)
        add_link_action = context_menu.addAction("Add Link to Tag")
        context_menu.addSeparator()
        rename_action = context_menu.addAction("Rename Tag")
        delete_action = context_menu.addAction("Delete Tag")

        action = context_menu.exec(self.tags_list.mapToGlobal(pos))

        if action == add_link_action:
            self.add_link_to_tag(item)

        if action == rename_action:
            self.rename_tag(item)
        elif action == delete_action:
            self.delete_tag()

    def add_tag(self):
        tag_name, ok = QInputDialog.getText(self, "Add New Tag", "Enter tag name:")
        if ok and tag_name:
            if tag_name in self.data_model.get_tags():
                QMessageBox.warning(self, "Warning", "Tag with this name already exists.")
                return

            self.data_model.data["tags"][tag_name] = []
            self.tags_list.addItem(tag_name)
            self.statusBar().showMessage(f"Tag '{tag_name}' added.", 3000)

    def add_link_to_selected_tag(self):
        current_item = self.tags_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Tag Selected", "Please select a tag from the list before adding a link.")
            return
        self.add_link_to_tag(current_item)

    def rename_tag(self, item):
        old_name = item.text()
        new_name, ok = QInputDialog.getText(self, "Rename Tag", "Enter new name:", text=old_name)

        if ok and new_name and new_name != old_name:
            if new_name in self.data_model.get_tags():
                QMessageBox.warning(self, "Warning", "Tag with this name already exists.")
                return

            # Update data model
            self.data_model.data["tags"][new_name] = self.data_model.data["tags"].pop(old_name)

            # Update UI
            item.setText(new_name)
            self.statusBar().showMessage(f"Tag '{old_name}' renamed to '{new_name}'.", 3000)

    def _parse_hf_url(self, url):
        # Regex to capture repo_id, type (blob/tree), and path
        pattern = r"https://huggingface.co/(?P<repo_id>[^/]+/[^/]+)/(?P<type>blob|tree)/[^/]+/(?P<path>.*)"
        match = re.match(pattern, url)
        if not match:
            # Try a simpler pattern for repos that might not have a full path
            pattern_simple = r"https://huggingface.co/(?P<repo_id>[^/]+/[^/]+)"
            match_simple = re.match(pattern_simple, url)
            if match_simple:
                 return {
                    "repo_id": match_simple.group("repo_id"),
                    "url_type": "folder", # Assume it's the root folder
                    "path": "."
                }
            return None

        data = match.groupdict()
        return {
            "repo_id": data["repo_id"],
            "url_type": "file" if data["type"] == "blob" else "folder",
            "path": data["path"]
        }

    def add_link_to_tag(self, item):
        tag_name = item.text()
        url, ok = QInputDialog.getText(self, f"Add Link to '{tag_name}'", "Enter HuggingFace URL:")

        if not (ok and url):
            return

        parsed_url = self._parse_hf_url(url)
        if not parsed_url:
            QMessageBox.warning(self, "Invalid URL", "Could not parse the HuggingFace URL.")
            return

        repo_id = parsed_url["repo_id"]
        path = parsed_url["path"]

        items_to_add = []

        if parsed_url["url_type"] == 'folder':
            # It's a folder, so we need to inspect its contents
            self.statusBar().showMessage(f"Inspecting folder: {repo_id}/{path}...", 5000)
            contents = self.hf_api.list_folder_contents(repo_id=repo_id, repo_type='model', folder_path=path)

            if contents is None:
                QMessageBox.critical(self, "API Error", f"Could not retrieve contents for {repo_id}/{path}.")
                return

            dialog = FolderSelectionDialog(contents, self)
            if dialog.exec():
                selected_items = dialog.get_selected_items()
                if not selected_items:
                    return

                if selected_items == ["__all__"]: # Special case for "add as single directory"
                    items_to_add.append({"repo_id": repo_id, "path": path, "type": "folder"})
                else:
                    for thing in selected_items:
                        item_type = "file" if hasattr(thing, 'size') else "folder"
                        items_to_add.append({"repo_id": repo_id, "path": thing.path, "type": item_type})
        else:
            # It's a single file
            items_to_add.append({"repo_id": repo_id, "path": path, "type": "file"})

        # Now, add the collected items to the data model
        if tag_name in self.data_model.data["tags"]:
            # Basic duplicate check
            existing_paths = [item.get('path') for item in self.data_model.data["tags"][tag_name]]
            new_items = [item for item in items_to_add if item.get('path') not in existing_paths]

            self.data_model.data["tags"][tag_name].extend(new_items)

            count = len(new_items)
            self.statusBar().showMessage(f"Added {count} new item(s) to tag '{tag_name}'.", 3000)
            self.on_tag_selected(item) # Refresh the view
        else:
             QMessageBox.critical(self, "Error", "Selected tag does not exist in data model.")

    def delete_tag(self):
        current_item = self.tags_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a tag to delete.")
            return

        tag_name = current_item.text()
        reply = QMessageBox.question(self, "Delete Tag", f"Are you sure you want to delete the tag '{tag_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # If the deleted tag is the current selection, clear the views
            if self.current_selection == ("tag", tag_name):
                self.current_selection = (None, None)
                self.tree_model.clear()
                self.raw_script_view.clear()

            # Update data model
            del self.data_model.data["tags"][tag_name]

            # Update UI
            self.tags_list.takeItem(self.tags_list.row(current_item))
            self.statusBar().showMessage(f"Tag '{tag_name}' deleted.", 3000)

    def show_schemes_context_menu(self, pos):
        item = self.schemes_list.itemAt(pos)
        if not item: return
        context_menu = QMenu(self)
        rename_action = context_menu.addAction("Rename Scheme")
        delete_action = context_menu.addAction("Delete Scheme")
        action = context_menu.exec(self.schemes_list.mapToGlobal(pos))
        if action == rename_action: self.rename_scheme(item)
        elif action == delete_action: self.delete_scheme()

    def add_scheme(self):
        scheme_name, ok = QInputDialog.getText(self, "Add New Scheme", "Enter scheme name:")
        if ok and scheme_name:
            if scheme_name in self.data_model.get_schemes():
                QMessageBox.warning(self, "Warning", "Scheme with this name already exists.")
                return
            self.data_model.data["schemes"][scheme_name] = []
            self.schemes_list.addItem(scheme_name)
            self.statusBar().showMessage(f"Scheme '{scheme_name}' added.", 3000)

    def rename_scheme(self, item):
        old_name = item.text()
        new_name, ok = QInputDialog.getText(self, "Rename Scheme", "Enter new name:", text=old_name)
        if ok and new_name and new_name != old_name:
            if new_name in self.data_model.get_schemes():
                QMessageBox.warning(self, "Warning", "Scheme with this name already exists.")
                return
            self.data_model.data["schemes"][new_name] = self.data_model.data["schemes"].pop(old_name)
            item.setText(new_name)
            self.statusBar().showMessage(f"Scheme '{old_name}' renamed to '{new_name}'.", 3000)

    def delete_scheme(self):
        current_item = self.schemes_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a scheme to delete.")
            return
        scheme_name = current_item.text()
        reply = QMessageBox.question(self, "Delete Scheme", f"Are you sure you want to delete '{scheme_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # If the deleted scheme is the current selection, clear the views
            if self.current_selection == ("scheme", scheme_name):
                self.current_selection = (None, None)
                self.tree_model.clear()
                self.raw_script_view.clear()

            del self.data_model.data["schemes"][scheme_name]
            self.schemes_list.takeItem(self.schemes_list.row(current_item))
            self.statusBar().showMessage(f"Scheme '{scheme_name}' deleted.", 3000)

    def scheme_drag_enter_event(self, event):
        if event.source() == self.structured_view:
            event.accept()
        else:
            event.ignore()

    def scheme_drop_event(self, event):
        target_item = self.schemes_list.itemAt(event.pos())
        if not target_item:
            return

        scheme_name = target_item.text()

        source_indexes = self.structured_view.selectionModel().selectedIndexes()
        source_items = [self.tree_model.itemFromIndex(index) for index in source_indexes if index.column() == 0]

        added_count = 0
        for s_item in source_items:
            item_data = s_item.data(Qt.UserRole)
            if not item_data: continue

            # Deep copy, create new uuid, and remove parent link
            new_item_data = copy.deepcopy(item_data)
            new_item_data["uuid"] = str(uuid.uuid4())
            new_item_data.pop("parent_uuid", None)

            self.data_model.data["schemes"][scheme_name].append(new_item_data)
            added_count += 1

        self.statusBar().showMessage(f"Added {added_count} item(s) to scheme '{scheme_name}'.", 3000)
        self.on_scheme_selected(target_item)


    def generate_script_file(self):
        script_content = self.raw_script_view.toPlainText()
        if not script_content or script_content.startswith("# Select a"):
            QMessageBox.warning(self, "Warning", "Cannot generate an empty script. Please select a tag or scheme with items.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Script", "download.sh", "Shell Scripts (*.sh);;All Files (*)")

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(script_content)
                self.statusBar().showMessage(f"Script saved to {file_path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save script file:\n{e}")

    def open_settings(self):
        dialog = SettingsDialog(self.data_model.data.get("settings", {}), self)
        if dialog.exec():
            self.data_model.data["settings"] = dialog.get_settings()
            self.statusBar().showMessage("Settings updated.", 3000)
            self.generate_script_preview() # Regenerate script with new settings

    def import_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Configuration", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            if self.data_model.load(file_path):
                self.load_data_to_ui()
                self.statusBar().showMessage(f"Successfully imported from {file_path}", 3000)
            else:
                QMessageBox.critical(self, "Error", f"Could not load configuration from {file_path}")

    def export_json(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Configuration", "hf_config.json", "JSON Files (*.json);;All Files (*)")
        if file_path:
            self.data_model.save(file_path)
            self.statusBar().showMessage(f"Configuration exported to {file_path}", 3000)

    def closeEvent(self, event):
        # Auto-save on closing
        self.save_config()
        event.accept()
