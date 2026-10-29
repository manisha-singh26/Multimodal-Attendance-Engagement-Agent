"""Initialize Git Repository and commit all project files using Dulwich."""
import os
import dulwich.porcelain as porcelain

repo_dir = os.path.dirname(os.path.abspath(__file__))

# 1. Initialize repository if .git doesn't exist
if not os.path.exists(os.path.join(repo_dir, ".git")):
    print(f"Initializing Git repository at {repo_dir}...")
    repo = porcelain.init(repo_dir)
else:
    repo = porcelain.open_repo(repo_dir)

# 2. Add all files
print("Staging files...")
porcelain.add(repo, paths=["."])

# 3. Create initial commit
try:
    commit_id = porcelain.commit(
        repo,
        message=b"Initial commit: Multimodal Attendance & Engagement Agent prototype & production deployment assets",
        author=b"Classroom Intelligence Agent <agent@local>",
        committer=b"Classroom Intelligence Agent <agent@local>"
    )
    print(f"Committed successfully! Commit hash: {commit_id.decode('ascii')}")
except Exception as e:
    print(f"Commit note: {e}")

# 4. Check status
status = porcelain.status(repo)
print(f"Tracked changes: {len(status.staged['modify']) + len(status.staged['add'])} staged, {len(status.untracked)} untracked.")

