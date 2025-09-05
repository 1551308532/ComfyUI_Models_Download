from huggingface_hub import HfApi

class HuggingFaceAPI:
    def __init__(self):
        self.api = HfApi()

    def list_folder_contents(self, repo_id, repo_type, folder_path):
        """
        Lists the contents of a folder in a Hugging Face repository.
        """
        try:
            # Note: repo_type can be 'model', 'dataset', or 'space'.
            # The PRD implies we are dealing with models, but this could be extended.
            items = self.api.list_repo_tree(repo_id=repo_id, path_in_repo=folder_path, repo_type=repo_type)
            return items
        except Exception as e:
            print(f"Error fetching folder contents for {repo_id}/{folder_path}: {e}")
            return None
