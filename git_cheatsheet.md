# 🔍 Check current branch
git branch

# 🔍 Check remote URL
git remote -v

# 🔍 Check upstream tracking
git branch -vv

# 🔍 Check working tree status
git status

# 🔍 Show root of current repo
git rev-parse --show-toplevel

# 🔍 Show full Git config
git config --list

# 🔍 Show remote URL for origin
git config --get remote.origin.url

# 🔍 Show upstream config for main
git config --get branch.main.remote
git config --get branch.main.merge

# 🛠️ Set upstream for current branch
git push --set-upstream origin main

# 🧹 Rename a misnamed branch
git branch -m old-name new-name

# 🧹 Delete a local branch
git branch -d branch-name

# 🧠 View commit history
git log --oneline --graph --decorate --all

# 🧠 Show a specific commit (if valid)
git show commit-hash