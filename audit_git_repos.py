import os
import subprocess

def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))

def run_git_command(path, command):
    try:
        result = subprocess.run(
            command,
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def audit_git_repos(root_dir):
    for folder in os.listdir(root_dir):
        full_path = os.path.join(root_dir, folder)
        if os.path.isdir(full_path) and is_git_repo(full_path):
            print(f"\n📁 Repo: {folder}")
            print("-" * 40)
            print("Branch:", run_git_command(full_path, "git branch --show-current"))
            print("Remote:", run_git_command(full_path, "git remote -v"))
            print("Upstream:", run_git_command(full_path, "git branch -vv"))
            print("Status:", run_git_command(full_path, "git status --short"))
        else:
            print(f"\n❌ Skipped: {folder} (not a Git repo)")

# 🔧 Replace this with your actual path
root_directory = r"C:\Users\pmpmt\Scripts_Cursor\251007-1-Change-title-to-filename-from-oneliner"
audit_git_repos(root_directory)