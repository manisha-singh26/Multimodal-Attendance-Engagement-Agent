"""Helper script to set remote and push repository to GitHub."""
import sys
import os
import dulwich.porcelain as porcelain

def push_repo(remote_url: str, branch: str = "main"):
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    repo = porcelain.open_repo(repo_dir)
    
    print(f"Connecting to remote: {remote_url}...")
    try:
        porcelain.remote_add(repo, "origin", remote_url)
    except KeyError:
        # Remote already exists, update it
        config = repo.get_config()
        config.set((b"remote", b"origin"), b"url", remote_url.encode("utf-8"))
        config.write_to_path()

    print(f"Pushing branch '{branch}' to origin...")
    try:
        porcelain.push(repo, "origin", f"refs/heads/{branch}".encode("utf-8"))
        print("Successfully pushed to GitHub!")
    except Exception as e:
        print(f"Push failed: {e}")
        print("Note: If using HTTPS authentication, make sure you provide a GitHub Personal Access Token (PAT) or SSH key.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python push_to_github.py <github_repo_url> [branch_name]")
        sys.exit(1)
    remote = sys.argv[1]
    b = sys.argv[2] if len(sys.argv) > 2 else "main"
    push_repo(remote, b)

