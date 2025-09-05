import React, { useState } from 'react';
import { Box, Typography, Menu, MenuItem, TextField, Dialog, DialogTitle, DialogContent, DialogActions, Button } from '@mui/material';
import { RichTreeView, TreeItem, treeItemClasses } from '@mui/x-tree-view';
import FolderIcon from '@mui/icons-material/Folder';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import { v4 as uuidv4 } from 'uuid';
import { produce } from 'immer';
import { styled } from '@mui/material/styles';

interface FileTreeViewProps {
    config: any;
    selectedItemKey: 'tags' | 'schemes';
    selectedItemName: string;
    onConfigChange: (newConfig: any) => void;
}

const StyledTreeItem = styled(TreeItem)(({ theme }) => ({
    [`& .${treeItemClasses.content}`]: {
        padding: theme.spacing(0.5, 1),
        borderRadius: theme.shape.borderRadius,
    },
}));

const FileTreeView: React.FC<FileTreeViewProps> = ({ config, selectedItemKey, selectedItemName, onConfigChange }) => {
    const [contextMenu, setContextMenu] = useState<{ mouseX: number; mouseY: number; item: any; } | null>(null);
    const [renameItem, setRenameItem] = useState<any | null>(null);
    const [renameText, setRenameText] = useState('');

    if (!selectedItemName) {
        return <Typography sx={{ p: 2, color: 'grey.500' }}>Select a tag or scheme to view its contents.</Typography>;
    }

    const items = config[selectedItemKey]?.[selectedItemName] || [];
    const itemsById: { [key: string]: any } = items.reduce((acc: any, item: any) => { acc[item.uuid] = item; return acc; }, {});

    const handleContextMenu = (event: React.MouseEvent, item: any) => {
        event.preventDefault();
        event.stopPropagation();
        setContextMenu({ mouseX: event.clientX - 2, mouseY: event.clientY - 4, item });
    };

    const handleClose = () => setContextMenu(null);

    const handleDelete = () => {
        if (!contextMenu?.item) return;
        const newConfig = produce(config, (draft: any) => {
            const itemsList = draft[selectedItemKey][selectedItemName];
            const allIdsToDelete = new Set<string>([contextMenu.item.uuid]);
            const q = [contextMenu.item.uuid];
            while (q.length > 0) {
                const parentId = q.shift()!;
                itemsList.forEach((i: any) => {
                    if (i.parent_uuid === parentId) {
                        allIdsToDelete.add(i.uuid);
                        q.push(i.uuid);
                    }
                });
            }
            draft[selectedItemKey][selectedItemName] = itemsList.filter((i: any) => !allIdsToDelete.has(i.uuid));
        });
        onConfigChange(newConfig);
        handleClose();
    };

    const handleRename = () => {
        if (!contextMenu?.item) return;
        setRenameItem(contextMenu.item);
        setRenameText(contextMenu.item.alias || contextMenu.item.path?.split('/').pop() || '');
        handleClose();
    };

    const handleCreateFolder = () => {
        const parentUuid = contextMenu?.item?.uuid;
        const newConfig = produce(config, (draft: any) => {
            if (!draft[selectedItemKey][selectedItemName]) {
                draft[selectedItemKey][selectedItemName] = [];
            }
            draft[selectedItemKey][selectedItemName].push({
                uuid: uuidv4(), alias: "New Folder", type: "virtual_folder",
                path: "", repo_id: "", parent_uuid: parentUuid,
            });
        });
        onConfigChange(newConfig);
        handleClose();
    };

    const handleRenameDialogClose = () => {
        if (!renameItem) return;
        const newConfig = produce(config, (draft: any) => {
            const item = draft[selectedItemKey][selectedItemName].find((i: any) => i.uuid === renameItem.uuid);
            if(item) item.alias = renameText;
        });
        onConfigChange(newConfig);
        setRenameItem(null);
    };

    const buildTree = (item: any) => ({
        id: item.uuid,
        label: item.alias || item.path?.split('/').pop() || 'New Folder',
        isFolder: item.type === 'folder' || item.type === 'virtual_folder',
        children: items.filter((child: any) => child.parent_uuid === item.uuid).map(buildTree),
        data: item,
    });

    const treeData = items.filter((item: any) => !item.parent_uuid).map(buildTree);

    return (
        <Box sx={{ mt: 2, height: 'calc(100vh - 150px)', overflowY: 'auto' }} onContextMenu={(e) => handleContextMenu(e, null)}>
            <RichTreeView
                items={treeData}
                aria-label="file system navigator"
                slots={{
                    item: (props) => (
                        <StyledTreeItem
                            {...props}
                            label={
                                <Box sx={{ display: 'flex', alignItems: 'center', py: 0.5 }} onContextMenu={(e) => handleContextMenu(e, props.item.data)}>
                                    {props.item.isFolder ? <FolderIcon sx={{ mr: 1, color: 'primary.main' }} /> : <InsertDriveFileIcon sx={{ mr: 1, color: 'grey.500' }} />}
                                    <Typography variant="body2">{props.item.label}</Typography>
                                </Box>
                            }
                        />
                    ),
                }}
            />
            <Menu open={contextMenu !== null} onClose={handleClose} anchorReference="anchorPosition" anchorPosition={contextMenu ? { top: contextMenu.mouseY, left: contextMenu.mouseX } : undefined}>
                <MenuItem onClick={handleCreateFolder}>New Virtual Folder</MenuItem>
                {contextMenu?.item && <MenuItem onClick={handleRename}>Rename</MenuItem>}
                {contextMenu?.item && <MenuItem onClick={handleDelete}>Delete</MenuItem>}
            </Menu>
            <Dialog open={renameItem !== null} onClose={() => setRenameItem(null)}>
                <DialogTitle>Rename Item</DialogTitle>
                <DialogContent>
                    <TextField autoFocus margin="dense" label="New Name" type="text" fullWidth variant="standard" value={renameText} onChange={(e) => setRenameText(e.target.value)} />
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setRenameItem(null)}>Cancel</Button>
                    <Button onClick={handleRenameDialogClose}>Save</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default FileTreeView;
