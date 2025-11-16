from urllib.parse import urlparse
import os
import shutil
from git import Repo

from core.utils import get_repo_name


class RepoCloner:
    def __init__(self, repo_url, base_target_dir="./repo"):
        self.repo_url = repo_url
        self.base_target_dir = base_target_dir
        self.repo_name = get_repo_name(repo_url)

    def clone_repo(
        self,
    ):
        """Clone repository into a folder named after the repo."""

        # Create target directory path
        target_dir = os.path.join(self.base_target_dir, self.repo_name)

        # Remove target directory if it exists and is not empty
        if os.path.exists(target_dir):
            if os.listdir(target_dir):  # Check if directory is not empty
                return target_dir
                # shutil.rmtree(target_dir)
                # print(f"Removed existing non-empty directory: {target_dir}")
            else:
                os.rmdir(target_dir)
                print(f"Removed existing empty directory: {target_dir}")

        # Create the base directory if it doesn't exist
        os.makedirs(self.base_target_dir, exist_ok=True)

        # Clone the repository
        Repo.clone_from(self.repo_url, target_dir)
        print(f"Repository cloned successfully to {target_dir}")

        return target_dir
