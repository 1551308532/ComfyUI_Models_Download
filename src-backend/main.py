import os
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List
from huggingface_hub import HfApi, hf_hub_url
from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError

# --- Constants & Configuration ---
CONFIG_FILE = "hf_config.json"

# --- FastAPI App Initialization ---
app = FastAPI()

# Configure CORS
# This is important for a separate frontend to be able to call the API.
# We'll allow all origins for local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

# --- Data Models (Pydantic) ---
class ConfigData(BaseModel):
    data: Dict[str, Any]

class NewTag(BaseModel):
    name: str

class NewScheme(BaseModel):
    name: str

class LinkRequest(BaseModel):
    url: str

class ScriptRequest(BaseModel):
    name: str
    type: str # 'tag' or 'scheme'
    items: List[Dict[str, Any]]


# --- Helper Functions ---
def get_config():
    """Loads the configuration from the JSON file."""
    if not os.path.exists(CONFIG_FILE):
        # Create a default config if it doesn't exist
        default_config = {
            "tags": {},
            "schemes": {},
            "settings": {
                "root_download_dir": "./downloads"
            }
        }
        save_config(default_config)
        return default_config

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config_data: dict):
    """Saves the configuration to the JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

# --- API Endpoints ---

@app.get("/api/config")
async def read_config():
    """Endpoint to get the entire configuration."""
    return get_config()

@app.post("/api/config")
async def write_config(config: ConfigData):
    """Endpoint to save the entire configuration."""
    try:
        save_config(config.data)
        return {"status": "success", "message": "Configuration saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tags")
async def create_tag(tag: NewTag):
    """Endpoint to create a new tag."""
    config = get_config()
    if tag.name in config["tags"]:
        raise HTTPException(status_code=400, detail="Tag with this name already exists.")

    config["tags"][tag.name] = []
    save_config(config)
    return {"status": "success", "message": f"Tag '{tag.name}' created."}

@app.delete("/api/tags/{tag_name}")
async def delete_tag(tag_name: str):
    """Endpoint to delete a tag."""
    config = get_config()
    if tag_name not in config["tags"]:
        raise HTTPException(status_code=404, detail="Tag not found.")

    del config["tags"][tag_name]
    save_config(config)
    return {"status": "success", "message": f"Tag '{tag_name}' deleted."}

@app.post("/api/schemes")
async def create_scheme(scheme: NewScheme):
    """Endpoint to create a new scheme."""
    config = get_config()
    if scheme.name in config["schemes"]:
        raise HTTPException(status_code=400, detail="Scheme with this name already exists.")

    config["schemes"][scheme.name] = []
    save_config(config)
    return {"status": "success", "message": f"Scheme '{scheme.name}' created."}

@app.delete("/api/schemes/{scheme_name}")
async def delete_scheme(scheme_name: str):
    """Endpoint to delete a scheme."""
    config = get_config()
    if scheme_name not in config["schemes"]:
        raise HTTPException(status_code=404, detail="Scheme not found.")

    del config["schemes"][scheme_name]
    save_config(config)
    return {"status": "success", "message": f"Scheme '{scheme_name}' deleted."}


def parse_hf_url(url: str):
    pattern = r"https://huggingface.co/(?P<repo_id>[^/]+/[^/]+)(?:/(?:tree|blob)/(?P<revision>[^/]+))?(?:/(?P<path>.*))?"
    match = re.match(pattern, url)
    if not match:
        return None
    data = match.groupdict()
    return {
        "repo_id": data["repo_id"],
        "path": data.get("path") or ".",
        "is_folder": "tree" in url or not data.get("path") or data.get("path") == "."
    }

@app.post("/api/inspect-link")
async def inspect_link(request: LinkRequest):
    """
    Inspects a HuggingFace URL. If it's a file, returns its details.
    If it's a folder, returns the list of its contents.
    """
    parsed_url = parse_hf_url(request.url)
    if not parsed_url:
        raise HTTPException(status_code=400, detail="Invalid HuggingFace URL format.")

    if not parsed_url["is_folder"]:
        # It's a file, return its details directly
        return {"type": "file", "details": parsed_url}

    try:
        api = HfApi()
        repo_contents = api.list_repo_tree(repo_id=parsed_url["repo_id"], path_in_repo=parsed_url["path"], repo_type='model')

        # Convert RepoFile and RepoFolder objects to serializable dicts
        contents_list = [
            {"path": item.path, "type": "folder" if "size" not in item.__dict__ else "file"}
            for item in repo_contents
        ]

        return {"type": "folder", "details": parsed_url, "contents": contents_list}
    except RepositoryNotFoundError:
        raise HTTPException(status_code=404, detail=f"Repository not found: {parsed_url['repo_id']}")
    except GatedRepoError:
        raise HTTPException(status_code=403, detail=f"Repository is gated. Please ensure you are logged in with huggingface-cli.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.post("/api/generate-script")
async def generate_script(request: ScriptRequest):
    """Generates the download.sh script for a given tag or scheme configuration."""
    items_by_uuid = {item["uuid"]: item for item in request.items}

    def get_full_path(item_uuid):
        path_parts = []
        curr_uuid = item_uuid
        while curr_uuid in items_by_uuid:
            item = items_by_uuid[curr_uuid]
            if item.get("type") == "virtual_folder":
                path_parts.append(item.get("alias", "unnamed_folder"))
            curr_uuid = item.get("parent_uuid")
        return "/".join(reversed(path_parts))

    config = get_config()
    default_root = config.get("settings", {}).get("root_download_dir", "./downloads")

    script_lines = ["#!/bin/bash", "# Auto-generated by HuggingFace Download Manager", ""]
    script_lines.append(f"# Configuration for: {request.type} '{request.name}'")
    script_lines.append("set -e")
    script_lines.append("export HF_HUB_ENABLE_HF_TRANSFER=1")
    script_lines.append(f'ROOT_DIR="${{1:-{default_root}}}"')
    script_lines.append('echo "Downloading files to $ROOT_DIR"')
    script_lines.append("")

    all_dirs = set()
    download_commands = []
    rename_commands = []

    for item in request.items:
        if item.get("type") == "virtual_folder":
            continue

        local_path = get_full_path(item.get("parent_uuid"))
        all_dirs.add(local_path)

        original_name = item.get("path").split('/')[-1]
        repo_id = item.get("repo_id")
        dl_path = f"$ROOT_DIR/{local_path}" if local_path else "$ROOT_DIR"

        download_commands.append(f"# Downloading: {item.get('path')}")
        download_commands.append(f"huggingface-cli download {repo_id} \"{item.get('path')}\" --repo-type model --local-dir \"{dl_path}\" --local-dir-use-symlinks False")

        alias = item.get("alias")
        if alias and alias != original_name:
            final_path = f"\"{dl_path}/{alias}\""
            original_path_full = f"\"{dl_path}/{original_name}\""
            rename_commands.append(f"# Renaming: {original_name} -> {alias}")
            rename_commands.append(f"mv {original_path_full} {final_path}")

    if all_dirs:
        script_lines.append("# --- Create Directories ---")
        for d in sorted(list(all_dirs)):
            if d: script_lines.append(f"mkdir -p \"$ROOT_DIR/{d}\"")
        script_lines.append("")

    script_lines.append("# --- Download Files ---")
    script_lines.extend(download_commands)
    script_lines.append("")

    if rename_commands:
        script_lines.append("# --- Rename Files ---")
        script_lines.extend(rename_commands)
        script_lines.append("")

    script_lines.append("echo \"Download script finished.\"")

    return {"script": "\n".join(script_lines)}


@app.get("/")
def read_root():
    return {"message": "HuggingFace Download Manager Backend is running."}
