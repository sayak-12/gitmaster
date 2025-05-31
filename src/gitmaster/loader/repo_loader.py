import os
import subprocess
import tempfile
from gitmaster.auth.github import get_token
from urllib.parse import urlparse

def is_github_repo(url: str) -> bool:
    return "github.com" in url

def clone_repo(url: str) -> str:
    token = get_token()
    parsed = urlparse(url)
    repo_path = parsed.path.strip("/")

    if token:
        # Authenticated clone
        clone_url = f"https://{token}:x-oauth-basic@github.com/{repo_path}.git"
    else:
        # Public repo clone
        print("Not logged in. Only public repos will be accessible.")
        clone_url = f"https://github.com/{repo_path}.git"

    target_dir = tempfile.mkdtemp(prefix="gitmaster_")
    try:
        subprocess.run(["git", "clone", "--depth", "1", clone_url, target_dir], check=True)
        print(f"Repo cloned to {target_dir}")
        return target_dir
    except subprocess.CalledProcessError as e:
        raise RuntimeError("❌ Failed to clone repo. Check URL or auth.") from e

def load_local_repo(path: str) -> str:
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"❌ Path does not exist: {abs_path}")
    print(f"✅ Loaded local repo from {abs_path}")
    return abs_path
