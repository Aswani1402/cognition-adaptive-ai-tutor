import sqlite3

DB_PATH = ("external/core_data/git_version_control.db")
def create_concept_resources_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_resources (
            concept_id TEXT PRIMARY KEY,
            topic TEXT,
            base_content TEXT,
            examples TEXT,
            key_points TEXT,
            misconceptions TEXT,
            real_world_use TEXT,
            next_concept_link TEXT
        );
    """)
# ============================================================
# G1: What is Version Control
# ============================================================

g1_id = "G1"
g1_topic = "What is Version Control"


g1_base_content = """
Version control is a system that records changes to files over time so that you can recall specific versions later. It allows you to track the history of your work, revert to earlier states, compare changes across time, and collaborate with others without overwriting each other's work.

Without version control, managing code across time and across teams becomes fragile. You end up with folders named "project_final", "project_final_v2", "project_final_REAL", and no clear understanding of what changed or why.

Version control solves this by storing every meaningful change as a snapshot with a timestamp and an author. You always know what changed, when it changed, and who changed it.

Two major categories of version control systems exist:

Centralized Version Control (CVCS):
A single central server holds the complete history. Developers check out files from the center and push changes back. If the server goes down, no one can access history. Examples: SVN, Perforce.

Distributed Version Control (DVCS):
Every developer holds a complete copy of the entire repository including its full history. There is no single point of failure. Work can happen offline. Merging is more flexible. Git is a distributed version control system.

Why Git became the standard:
- Every clone is a full backup of the project history
- Branching and merging are fast and lightweight
- Works offline — you do not need a server to commit
- Designed for speed even on large codebases
- Powers GitHub, GitLab, and Bitbucket — the backbone of modern software collaboration

Core vocabulary to understand before using Git:
- Repository (repo) — the container that stores your project and its full history
- Commit — a saved snapshot of your changes at a point in time
- Branch — an independent line of development
- Merge — combining changes from one branch into another
- Clone — copying a remote repository to your local machine
- Push — sending your local commits to a remote repository
- Pull — fetching and integrating remote changes into your local branch

Version control is not optional in professional software development. It is the foundation on which all collaboration, code review, deployment, and rollback depend.
"""

g1_examples = """
Example 1 — What version control prevents:
# Without version control — chaos
project_v1/
project_v2/
project_final/
project_final_FIXED/
project_final_REAL_THIS_ONE/

# With version control — one clean folder, full history inside
my_project/   ← Git manages every version internally

Example 2 — Initializing a Git repository:
mkdir my_project
cd my_project
git init
# Output: Initialized empty Git repository in /my_project/.git/

Example 3 — Checking the status of a repository:
git status
# Output:
# On branch main
# nothing to commit, working tree clean

Example 4 — Viewing full project history:
git log --oneline
# a3f2c91 Fix login bug
# b81d003 Add user authentication
# 4c9e112 Initial project setup

Each line is a commit — a saved snapshot with a unique ID, message, and author.

Example 5 — The difference between local and remote:
# Local repository — lives on your machine
# Remote repository — lives on GitHub, GitLab, or a server

git remote add origin https://github.com/user/project.git
git push origin main
# Your local commits are now backed up on the remote server
"""

g1_key_points = """
- Version control tracks every change to files over time
- Git is a distributed version control system — every clone has the full history
- A repository is the container storing your project and its complete history
- A commit is a saved snapshot of your work at a specific moment
- Git works offline — you do not need a network connection to commit
- Centralized systems have one server; distributed systems give every developer a full copy
- Git is the industry standard — it powers GitHub, GitLab, and Bitbucket
- Without version control, tracking history, rolling back, and collaborating safely is nearly impossible
- Git stores history as a chain of commits, not as file differences alone
- Every commit has a unique identifier (SHA hash), an author, a timestamp, and a message
"""

g1_misconceptions = """
- "Git and GitHub are the same thing" — Git is the version control system. GitHub is a hosting platform for Git repositories. Git exists without GitHub. GitHub requires Git.
- "Version control is only for large teams" — Even solo developers benefit from version control. It provides undo history, safe experimentation, and backup at every stage of a project.
- "You need internet to use Git" — Git is distributed. You can commit, branch, and view history entirely offline. Internet is only needed when pushing to or pulling from a remote server.
- "Deleting a file removes it from history" — Git tracks deletions as commits. Deleting a file and committing records the deletion. The file still exists in previous commits and can be restored.
- "Git automatically saves your work" — Git only saves when you explicitly run git commit. Unsaved changes in your working directory are not protected by Git until committed.
- "Version control is complicated and only for advanced developers" — Basic Git (init, add, commit, push) can be learned in one session and immediately protects your work.
"""

g1_real_world_use = """
- Every major software company uses Git as the foundation of their development workflow
- Open source projects on GitHub use Git so thousands of contributors can work simultaneously
- Code review processes depend on Git branches and pull requests to review changes before merging
- Continuous integration and deployment pipelines trigger automatically from Git commits and pushes
- Bug tracking and rollback depend on Git history — you can identify exactly which commit introduced a bug
- Teams use Git tags to mark release versions, making deployment tracking precise and reliable
"""

g1_next_concept_link = """
Now that you understand what version control is and why Git exists, the next concept — Git Repositories — explains what a repository actually contains internally, how to create one, how to clone an existing one, and how local and remote repositories relate to each other.
"""

# ============================================================
# G2: Git Repositories
# ============================================================

g2_id = "G2"
g2_topic = "Git Repositories"

g2_base_content = """
A Git repository is a directory that Git manages. It contains your project files and a hidden folder called .git that stores the entire history of your project — every commit, every branch, every tag, and every piece of metadata Git needs to function.

When you run git init, Git creates that .git folder inside your directory. From that point on, Git tracks everything that happens in that directory. You do not need to configure a server. Everything starts locally.

Two types of repositories:

Local repository:
Lives on your machine. You work here — writing code, staging changes, committing snapshots. Git stores history in the .git folder inside your project directory.

Remote repository:
Lives on a server — GitHub, GitLab, Bitbucket, or your own server. It is a shared copy of the repository that your team pushes to and pulls from. It acts as the central point of collaboration, but Git itself does not require it.

What lives inside .git:
- HEAD — a pointer to the current branch you are on
- objects/ — the actual stored content of commits, trees, and blobs
- refs/ — references to branches and tags
- config — repository-level configuration (remote URLs, user settings)
- index — the staging area, tracking what will go into the next commit

Creating a repository from scratch:
mkdir project
cd project
git init

Cloning an existing remote repository:
git clone https://github.com/user/project.git
# This downloads the full repository including all history

Connecting a local repo to a remote:
git remote add origin https://github.com/user/project.git

Checking your remotes:
git remote -v
# origin  https://github.com/user/project.git (fetch)
# origin  https://github.com/user/project.git (push)

The three states of files in Git:
1. Modified — you changed the file but have not staged it yet
2. Staged — you marked the change to go into the next commit
3. Committed — the change is safely stored in the local repository history

Understanding these three states is essential for understanding how Git moves your work from editing to history.
"""

g2_examples = """
Example 1 — Creating a new local repository:
mkdir my_app
cd my_app
git init
# Output: Initialized empty Git repository in /my_app/.git/

ls -a
# .  ..  .git

Example 2 — Cloning a remote repository:
git clone https://github.com/torvalds/linux.git
# Downloads the entire Linux kernel repository with full history

cd linux
git log --oneline -5
# Shows the last 5 commits

Example 3 — Checking what remote a local repo connects to:
git remote -v
# origin  https://github.com/user/project.git (fetch)
# origin  https://github.com/user/project.git (push)

Example 4 — Adding a remote to an existing local repo:
git init
git remote add origin https://github.com/user/new_project.git
git remote -v
# origin  https://github.com/user/new_project.git (fetch)
# origin  https://github.com/user/new_project.git (push)

Example 5 — Viewing the .git folder structure:
ls .git
# HEAD  branches  config  description  hooks  index  info  objects  refs

cat .git/HEAD
# ref: refs/heads/main
# This tells you which branch you are currently on
"""

g2_key_points = """
- A Git repository is a directory managed by Git, containing your files and a .git folder
- The .git folder holds the entire history — commits, branches, tags, and configuration
- git init creates a new local repository in the current directory
- git clone downloads a complete copy of a remote repository including all history
- A local repository lives on your machine; a remote repository lives on a server
- git remote add origin connects a local repo to a remote server
- Files in Git exist in three states: modified, staged, or committed
- The staging area (index) is where you prepare changes before committing them
- Deleting the .git folder destroys the entire history of your project
- A repository is self-contained — every clone is a full independent copy with complete history
"""

g2_misconceptions = """
- "A repository is just a folder with code" — A repository is a folder managed by Git. The .git subfolder is what makes it a repository. Without it, it is just a directory.
- "You need a remote repository to use Git" — Git works entirely locally. Remote repositories are for collaboration and backup, not for Git to function.
- "git clone and git pull are the same" — git clone creates a brand new local copy of a remote repository. git pull fetches and merges changes into an already existing local repository.
- "Removing files from the working directory removes them from the repository" — Deletion must be committed. The file remains in history and can be restored from any previous commit.
- "The remote repository is the main copy" — In distributed Git, no single copy is more authoritative than another by design. The remote is conventionally treated as the shared reference point, but it is not technically superior.
- "git init and git clone do the same thing" — git init creates an empty local repository. git clone copies a full remote repository with all its history and content.
"""

g2_real_world_use = """
- Every software project using Git starts with git init or git clone as its first action
- Teams clone the central remote repository to get a full local working copy before contributing
- Companies host private remote repositories on GitHub, GitLab, or internal servers to protect proprietary code
- Open source maintainers expose public repositories that anyone can clone and contribute to
- Backup strategies rely on remote repositories — if your machine fails, the full history is safe on the remote
- Repository structure (mono-repo vs multi-repo) is an architectural decision that affects how large teams organize their codebase
"""

g2_next_concept_link = """
Now that you understand what a repository is and how local and remote repositories relate, the next concept — Commits and History — explains how Git actually records changes, what a commit contains internally, and how to navigate and inspect the history of a repository.
"""

# ============================================================
# G3: Commits and History
# ============================================================

g3_id = "G3"
g3_topic = "Commits and History"

g3_base_content = """
A commit is a saved snapshot of your project at a specific point in time. It is the fundamental unit of history in Git. Every commit records what changed, who changed it, when it was changed, and why — through the commit message.

Git does not store commits as full file copies. It stores them as snapshots of the entire project state, using a content-addressed system. If a file did not change between two commits, Git does not duplicate it — it just points to the same stored content. This makes Git storage efficient.

What a commit contains:
- A unique SHA-1 hash — a 40-character identifier like a3f2c91b...
- The author name and email
- The timestamp of when it was committed
- The commit message describing the change
- A pointer to the parent commit (the commit before it)
- A snapshot of the staged files at that moment

The three-step commit workflow:
1. Modify files in your working directory
2. Stage the changes you want to include (git add)
3. Commit the staged changes to history (git commit)

The staging area is intentional. It lets you be selective — you can modify ten files but commit only three of them in a focused, meaningful commit.

Writing good commit messages:
A good commit message answers: "What does this commit do?"
- Bad: "fix stuff"
- Bad: "update"
- Good: "Fix null pointer error in user authentication flow"
- Good: "Add password strength validation to registration form"

The convention is: short imperative summary under 72 characters, optionally followed by a blank line and a detailed explanation.

Navigating history:
- git log — shows full commit history
- git log --oneline — compact one-line view
- git show <hash> — shows the full details of a specific commit
- git diff — shows unstaged changes
- git diff --staged — shows staged but not yet committed changes

Reverting and undoing:
- git revert <hash> — creates a new commit that undoes a previous commit (safe for shared history)
- git reset --soft HEAD~1 — moves the branch pointer back one commit, keeps changes staged
- git reset --hard HEAD~1 — moves back one commit and discards all changes permanently
"""

g3_examples = """
Example 1 — The full commit workflow:
# Step 1: Create or modify a file
echo "print('hello')" > hello.py

# Step 2: Stage it
git add hello.py

# Step 3: Commit it
git commit -m "Add hello world script"
# Output: [main a3f2c91] Add hello world script

Example 2 — Staging selectively:
# You changed three files but only want to commit two
git add login.py
git add auth.py
# forms.py is intentionally left out of this commit
git commit -m "Refactor login and auth modules"

Example 3 — Viewing commit history:
git log --oneline
# a3f2c91 Fix null pointer in auth flow
# b81d003 Add user registration endpoint
# 4c9e112 Initial project structure

Example 4 — Inspecting a specific commit:
git show a3f2c91
# Shows author, date, message, and the exact diff of what changed

Example 5 — Undoing safely with revert:
git revert a3f2c91
# Creates a new commit that undoes the changes from a3f2c91
# The original commit remains in history — safe for shared branches

Example 6 — Undoing locally with reset:
git reset --soft HEAD~1
# Moves back one commit
# Changes are kept and remain staged — you can re-commit with a better message

git reset --hard HEAD~1
# Moves back one commit
# Changes are permanently discarded — use with caution
"""

g3_key_points = """
- A commit is a saved snapshot of your project at a specific point in time
- Every commit has a unique SHA hash, author, timestamp, message, and parent pointer
- The three-step workflow is: modify → stage (git add) → commit (git commit)
- The staging area lets you choose exactly which changes go into each commit
- git log shows the full history; git log --oneline shows a compact view
- Good commit messages are imperative, specific, and under 72 characters
- git revert undoes a commit safely by creating a new commit — preserves history
- git reset --soft moves the branch pointer back but keeps changes staged
- git reset --hard moves back and permanently discards changes — dangerous
- Git stores snapshots efficiently — unchanged files are not duplicated between commits
- Every commit points to its parent, forming a linked chain of history
- git show <hash> displays the full content and diff of any specific commit
"""

g3_misconceptions = """
- "git add saves my work" — git add only stages changes. Nothing is saved to Git history until git commit is run.
- "I should commit everything in one big commit at the end" — Small, focused commits with clear messages are far more useful. They make history readable, bugs easier to find, and rollbacks more precise.
- "Commit messages do not matter" — Commit messages are the documentation of your project's evolution. In a team, poor messages make debugging and code review significantly harder.
- "git reset is safe to use on shared branches" — git reset rewrites history. If others have already pulled the commits you reset, their history diverges from yours, causing serious conflicts.
- "git revert and git reset do the same thing" — git revert adds a new undo commit and preserves history. git reset moves the branch pointer and can erase commits. They have completely different effects.
- "You can only commit entire files" — The staging area lets you stage individual lines within a file using git add -p (patch mode), giving you fine-grained control over what each commit contains.
"""

g3_real_world_use = """
- Every code change in professional software is tracked as a commit, creating an auditable history of the project
- Code reviews on GitHub and GitLab review specific commits or sets of commits before merging
- Debugging uses git bisect to binary search through commit history to find exactly which commit introduced a bug
- Deployment pipelines trigger from specific commits or tags, making releases traceable to exact code states
- Commit history serves as documentation — experienced developers read git log before touching unfamiliar code
- Rollback in production is done by reverting to a previous known-good commit
"""

g3_next_concept_link = """
Commits form a linear chain of history on a single line of development. The next concept — Branches — explains how Git allows you to diverge from that main line, work on features or fixes in isolation, and later bring those changes back together without disrupting the stable codebase.
"""

# ============================================================
# G4: Branches
# ============================================================

g4_id = "G4"
g4_topic = "Branches"

g4_base_content = """
A branch in Git is a lightweight, movable pointer to a specific commit. It lets you diverge from the main line of development and work on something — a feature, a bug fix, an experiment — in complete isolation, without affecting the rest of the codebase.

Branching is one of Git's most powerful features. Unlike older version control systems where branching was slow and expensive, Git branches are nearly instant because a branch is simply a pointer, not a copy of your files.

When you make a commit on a branch, the branch pointer moves forward to the new commit automatically. The other branches remain where they were, unaffected.

The default branch:
When you create a repository, Git creates a default branch. Historically it was called master. Most platforms now default to main. Both are just names — there is nothing technically special about them compared to any other branch.

HEAD:
HEAD is a special pointer that tells Git which branch you are currently on. When you switch branches, HEAD moves. When you make a commit, the current branch pointer moves forward and HEAD follows.

Common branch commands:
- git branch — list all local branches
- git branch feature-login — create a new branch
- git checkout feature-login — switch to a branch
- git switch feature-login — modern alternative to checkout
- git checkout -b feature-login — create and switch in one step
- git switch -c feature-login — modern equivalent
- git branch -d feature-login — delete a branch (safe, checks for unmerged changes)
- git branch -D feature-login — force delete a branch

Branch naming conventions used in professional teams:
- feature/user-authentication
- fix/null-pointer-login
- hotfix/payment-crash
- release/v2.1.0
- chore/update-dependencies

The main workflow using branches:
1. Create a branch from main for your feature
2. Make commits on that branch
3. When ready, merge or rebase the branch back into main
4. Delete the feature branch after merging

This keeps main stable and clean. Every feature lives in its own branch until it is ready and reviewed.
"""

g4_examples = """
Example 1 — Creating and switching to a branch:
git checkout -b feature-login
# Created and switched to a new branch 'feature-login'

# Equivalent modern syntax:
git switch -c feature-login

Example 2 — Listing branches:
git branch
# * feature-login     ← asterisk shows current branch
#   main

git branch -a
# Shows both local and remote branches

Example 3 — Making commits on a branch without affecting main:
git switch -c feature-signup

# Make changes
echo "signup logic" > signup.py
git add signup.py
git commit -m "Add signup module"

# Switch back to main — signup.py does not exist here
git switch main
ls
# signup.py is not here — it exists only on feature-signup

Example 4 — Deleting a branch after merging:
git switch main
git merge feature-login
git branch -d feature-login
# Deleted branch feature-login — work is now in main

Example 5 — Checking where HEAD points:
cat .git/HEAD
# ref: refs/heads/feature-login
# HEAD is currently pointing to feature-login branch

Example 6 — Remote branches:
git branch -r
# origin/main
# origin/feature-login

git checkout -b feature-login origin/feature-login
# Creates a local branch that tracks the remote branch
"""

g4_key_points = """
- A branch is a lightweight pointer to a specific commit — not a copy of files
- Creating a branch in Git is nearly instant regardless of repository size
- HEAD is a pointer that tracks which branch you are currently on
- git checkout -b or git switch -c creates and switches to a new branch in one step
- Commits made on a branch do not affect other branches
- The default branch is commonly named main or master — it has no technical special status
- git branch lists all local branches; the asterisk marks the current one
- git branch -d safely deletes a branch; git branch -D force deletes it
- Branch naming conventions (feature/, fix/, hotfix/) help teams communicate intent clearly
- Remote branches (origin/main) exist on the server and are tracked locally
- Branches should be deleted after merging to keep the repository clean
- The typical professional workflow is: branch → develop → review → merge → delete
"""

g4_misconceptions = """
- "Branching creates a copy of all my files" — A branch is just a pointer to a commit. No files are duplicated. Creating a branch is an operation that takes milliseconds.
- "I should do all my work on main" — Working directly on main is risky in team settings. If your work breaks something, it affects everyone. Branches isolate your work until it is ready.
- "Deleting a branch deletes the commits" — Deleting a branch removes the pointer, not the commits. The commits remain in Git's object store. However, without a branch pointing to them, they become unreachable and will eventually be cleaned up by garbage collection.
- "HEAD always points to the latest commit" — HEAD points to the current branch, which points to the latest commit on that branch. In detached HEAD state, HEAD points directly to a commit rather than a branch.
- "Remote branches and local branches are always in sync" — They diverge as soon as you make local commits or the remote is updated by someone else. git fetch updates your view of remote branches without changing your local work.
- "You need to push a branch before others can work on it" — A branch is purely local until you push it. git push origin feature-login publishes the branch to the remote server.
"""

g4_real_world_use = """
- Every feature in a professional codebase is developed on its own branch to isolate work in progress
- Pull requests and merge requests on GitHub and GitLab are built around branch-based workflows
- Git Flow and GitHub Flow are structured branching strategies used by teams to manage releases and features
- Hotfix branches allow critical production bugs to be fixed without interfering with ongoing feature development
- Continuous integration systems run automated tests on every branch push before code is allowed to merge
- Code review is done per branch — reviewers examine the commits on a feature branch before approving the merge
"""

g4_next_concept_link = """
Branches let you diverge. The next concept — Merge and Conflict Basics — explains how to bring those diverged lines of development back together, what happens when two branches change the same part of a file, and how to resolve those conflicts correctly.
"""

# ============================================================
# G5: Merge and Conflict Basics
# ============================================================

g5_id = "G5"
g5_topic = "Merge and Conflict Basics"

g5_base_content = """
Merging is the process of combining the work from one branch into another. When a feature branch is complete and reviewed, it is merged back into the main branch so its changes become part of the stable codebase.

Git merges by finding the common ancestor commit between two branches, then applying the changes from both sides on top of that ancestor.

Two types of merges:

Fast-forward merge:
Happens when the target branch (main) has not diverged from the source branch (feature). Git simply moves the main pointer forward to the latest commit on the feature branch. No merge commit is created. The history stays linear.

Three-way merge:
Happens when both branches have diverged — each has commits the other does not have. Git creates a new merge commit that has two parents: the tip of each branch. This merge commit represents the point where the two histories joined.

What is a merge conflict:
A merge conflict occurs when two branches modify the same lines of the same file in different ways. Git cannot automatically decide which version to keep. It pauses the merge and asks you to resolve it manually.

Git marks conflicts in the file using conflict markers:
<<<<<<< HEAD
your current branch version
=======
the incoming branch version
>>>>>>> feature-branch

You must edit the file, remove the markers, choose or combine the content, then stage the resolved file and commit.

Steps to resolve a conflict:
1. Run git merge — Git reports which files have conflicts
2. Open the conflicted files — look for the <<< === >>> markers
3. Edit the file to the correct final state
4. git add the resolved file
5. git commit to complete the merge

Avoiding conflicts:
- Communicate with teammates about which files they are working on
- Keep branches short-lived — the longer a branch diverges, the more conflicts accumulate
- Merge from main into your branch frequently to stay current
- Keep commits small and focused
"""

g5_examples = """
Example 1 — Fast-forward merge:
git switch main
git merge feature-login
# Output: Fast-forward
# No new merge commit — main pointer moves forward

Example 2 — Three-way merge:
git switch main
git merge feature-signup
# Output: Merge made by the 'recursive' strategy.
# A new merge commit is created with two parents

Example 3 — Triggering and seeing a conflict:
# On main: login.py has "def login(): return 'v1'"
# On feature: login.py has "def login(): return 'v2'"

git switch main
git merge feature
# CONFLICT (content): Merge conflict in login.py
# Automatic merge failed; fix conflicts and then commit the result.

cat login.py
# <<<<<<< HEAD
# def login(): return 'v1'
# =======
# def login(): return 'v2'
# >>>>>>> feature

Example 4 — Resolving a conflict:
# Edit login.py manually to the correct version:
# def login(): return 'v2'   ← chosen resolution

git add login.py
git commit -m "Merge feature branch — resolve login conflict"

Example 5 — Aborting a merge in progress:
git merge --abort
# Cancels the merge and returns to pre-merge state

Example 6 — Merging with a commit message:
git merge feature-login --no-ff -m "Merge feature-login into main"
# --no-ff forces a merge commit even if fast-forward is possible
# Preserves the branch history in the log
"""

g5_key_points = """
- Merging combines the work from one branch into another
- Fast-forward merge moves the pointer forward when no divergence has occurred — no merge commit
- Three-way merge creates a merge commit when both branches have diverged
- A merge conflict occurs when two branches change the same lines of a file differently
- Git marks conflicts with <<<<<<< HEAD, =======, and >>>>>>> markers
- Resolving a conflict requires manually editing the file, then staging and committing it
- git merge --abort cancels a merge in progress and restores the pre-merge state
- --no-ff forces a merge commit even when a fast-forward is possible, preserving branch history
- Short-lived branches and frequent syncing with main reduce the frequency and severity of conflicts
- git status during a merge shows which files have conflicts and which are resolved
- After resolving all conflicts, git commit completes the merge
"""

g5_misconceptions = """
- "Merge conflicts mean something went wrong" — Conflicts are a normal part of collaborative development. They occur naturally when two people modify the same code. They are expected, not errors.
- "Git can always figure out the correct merge automatically" — Git resolves non-overlapping changes automatically. When the same lines are changed differently, Git has no way to know which version is correct — it needs human judgment.
- "Fast-forward and three-way merges produce the same result" — Fast-forward moves a pointer and creates no merge commit. Three-way merge creates a merge commit with two parents. They produce different histories.
- "Once you start a merge you must finish it" — git merge --abort cancels the merge cleanly and returns you to the state before the merge began.
- "Resolving a conflict means picking one version and deleting the other" — Sometimes the correct resolution combines content from both sides. You edit the file to the correct final state, which may be a hybrid of both branches.
- "Merging is the only way to combine branches" — Rebasing is another strategy for integrating branches. It replays commits on top of another branch instead of creating a merge commit, resulting in a linear history.
"""

g5_real_world_use = """
- Pull requests on GitHub complete with a merge button that integrates a feature branch into main after review
- Continuous integration runs all tests before a merge is allowed, ensuring conflicts do not break the build
- Long-lived feature branches in large teams accumulate more conflicts — teams use frequent integration to minimize this
- Production hotfixes are merged into both main and active development branches to keep all lines consistent
- Merge strategies (squash merge, rebase merge, regular merge) are team-level decisions that affect how history is recorded
- Release management depends on merging release branches back into main after final testing is complete
"""

g5_next_concept_link = """
Basic merging combines branches at their current state. The next concept — Interactive Rebase — gives you surgical control over commit history: reordering, squashing, editing, and cleaning up commits before they are shared with the team.
"""

# ============================================================
# G6: Interactive Rebase
# ============================================================

g6_id = "G6"
g6_topic = "Interactive Rebase"

g6_base_content = """
Rebase is the process of moving or replaying commits from one branch onto another base commit. Instead of creating a merge commit to join two branches, rebase rewrites the commit history so it appears as if your work was always built on top of the latest state of the target branch.

Interactive rebase extends this with a menu-driven interface that lets you rewrite, reorder, squash, edit, or drop individual commits before sharing them.

Regular rebase vs interactive rebase:
- Regular rebase: git rebase main — replays your branch commits on top of main, cleanly
- Interactive rebase: git rebase -i HEAD~N — opens an editor to manipulate the last N commits

Interactive rebase commands:
- pick — keep the commit as-is
- reword — keep the commit but edit its message
- edit — pause at this commit so you can amend it
- squash — combine this commit with the one above it, merge messages
- fixup — combine this commit with the one above it, discard this message
- drop — delete this commit entirely
- reorder — move lines up or down in the editor to reorder commits

When to use interactive rebase:
- Before pushing a feature branch: clean up "WIP" and "fix typo" commits into meaningful ones
- To squash multiple small commits into a single clean commit
- To reorder commits so the history reads logically
- To edit a commit message that was already committed
- To split a large commit into smaller focused ones

The golden rule of rebasing:
Never rebase commits that have already been pushed to a shared remote branch. Rebase rewrites history — new SHA hashes are created for every rebased commit. If others have already pulled those commits, their history diverges from yours, causing serious problems.

Rebase vs Merge:
- Merge preserves the full history including branch topology — you see where branches diverged and rejoined
- Rebase creates a linear history — cleaner to read but hides the original branching structure
- Neither is universally better — teams choose based on their workflow preferences
"""

g6_examples = """
Example 1 — Regular rebase to stay current with main:
git switch feature-login
git rebase main
# Replays your feature commits on top of the latest main
# Linear history — no merge commit

Example 2 — Opening interactive rebase for last 4 commits:
git rebase -i HEAD~4
# Opens your default editor with:
# pick a3f2c91 Add login form
# pick b81d003 fix typo
# pick 4c9e112 WIP
# pick d72e881 Finalize login validation

Example 3 — Squashing commits:
# Change the editor content to:
# pick a3f2c91 Add login form
# squash b81d003 fix typo
# squash 4c9e112 WIP
# squash d72e881 Finalize login validation

# Result: all four commits become one single commit
# Git opens another editor for you to write the combined message

Example 4 — Rewording a commit message:
# Change the editor content to:
# reword a3f2c91 Add login form
# pick b81d003 Next commit

# Git pauses and opens an editor for you to write the new message for a3f2c91

Example 5 — Dropping a commit:
# pick a3f2c91 Add login form
# drop b81d003 Accidental debug print added
# pick 4c9e112 Final login logic

# The drop commit is permanently removed from history

Example 6 — Force pushing after rebase:
# After rebasing a branch that was already pushed:
git push --force-with-lease origin feature-login
# --force-with-lease is safer than --force
# It checks that no one else pushed to the branch before overwriting
"""

g6_key_points = """
- Rebase moves commits onto a new base, creating a linear history without merge commits
- Interactive rebase (git rebase -i HEAD~N) opens an editor to manipulate the last N commits
- pick keeps a commit, squash combines it with the one above, drop removes it, reword edits its message
- Interactive rebase is used to clean up history before sharing a feature branch
- Never rebase commits already pushed to a shared branch — it rewrites history and causes divergence
- Rebase and merge both integrate branches but produce different histories
- Merge preserves branch topology; rebase creates a flat linear history
- After rebasing a pushed branch, force push is required: git push --force-with-lease
- --force-with-lease is safer than --force — it checks for upstream changes before overwriting
- Squashing turns multiple small messy commits into a single clean meaningful commit
- fixup combines commits silently, discarding the squashed message; squash lets you edit the combined message
"""

g6_misconceptions = """
- "Rebase and merge do the same thing" — Both integrate branch changes, but rebase rewrites history to be linear while merge creates a merge commit that preserves the branching structure.
- "Interactive rebase only works on the last commit" — Interactive rebase works on any number of recent commits. HEAD~10 gives you the last 10 commits to manipulate.
- "Squashing commits loses information" — The code changes are preserved in the squashed commit. Only the individual commit boundaries and their messages are merged. The actual diff is combined.
- "Rebasing is always better than merging because history is cleaner" — Neither is always better. Rebase hides real development history. Merge preserves it. The right choice depends on team convention.
- "You can safely rebase any branch anytime" — Only rebase commits that exist only in your local branch. Once commits are on a shared remote branch and others have pulled them, rebasing creates serious conflicts.
- "git rebase -i requires you to squash everything" — You choose what to do with each commit. You can pick some, squash others, and drop a few in the same interactive session.
"""

g6_real_world_use = """
- Teams use interactive rebase before opening a pull request to present a clean, reviewable commit history
- Open source projects often require contributors to squash their commits before a pull request is accepted
- Rebasing onto main before merging reduces conflicts and keeps the merge simple and clean
- Code review is easier when a feature branch has 3 meaningful commits rather than 47 WIP commits
- Fixup commits (small corrections to earlier commits) are cleaned up with interactive rebase before pushing
- Some teams enforce a linear history policy on main, requiring all merges to be done via rebase rather than merge commits
"""

g6_next_concept_link = """
Interactive rebase gives you control over individual commits within a repository. The next concept — Submodules — moves to a higher level: managing entire external repositories embedded inside your own, which is how large projects handle shared libraries and dependencies tracked under version control.
"""

# ============================================================
# G7: Submodules
# ============================================================

g7_id = "G7"
g7_topic = "Submodules"

g7_base_content = """
A Git submodule is a repository embedded inside another repository. The outer repository (the parent) contains a reference to a specific commit in the inner repository (the submodule), rather than copying its files directly.

Submodules are used when a project depends on another project that is itself version-controlled. Instead of copying the dependency's code directly, you link to it as a submodule. The parent repository tracks exactly which version of the submodule it uses.

How submodules work internally:
- The parent repository stores a .gitmodules file listing the submodule paths and their remote URLs
- Each submodule is pinned to a specific commit — not a branch, but an exact commit hash
- The parent repository does not track the submodule's files directly — it tracks the commit pointer
- When you clone the parent, the submodule directories are empty until you initialize and update them

Key files:
- .gitmodules — configuration file listing submodule paths and URLs
- The submodule entry in .git/config — local configuration after init

Adding a submodule:
git submodule add https://github.com/user/library.git external/library

Cloning a repo with submodules:
git clone --recurse-submodules https://github.com/user/project.git

If you already cloned without --recurse-submodules:
git submodule init
git submodule update

Updating a submodule to a newer commit:
cd external/library
git pull origin main
cd ../..
git add external/library
git commit -m "Update library submodule to latest commit"

Removing a submodule:
git submodule deinit external/library
git rm external/library
rm -rf .git/modules/external/library

Strengths of submodules:
- Pin a dependency to an exact known-good version
- Keep the dependency's full history accessible
- Changes to the dependency require explicit updates — accidental drift is prevented

Weaknesses of submodules:
- Cloning requires extra steps (--recurse-submodules or manual init/update)
- Moving to a new submodule commit requires manual steps in every developer's environment
- Submodule state is easy to leave out of sync — the parent points to a commit the developer has not fetched
- Team members often forget to update submodules after pulling, causing subtle build failures
"""

g7_examples = """
Example 1 — Adding a submodule:
git submodule add https://github.com/user/shared-library.git libs/shared
# Creates libs/shared/ directory containing the submodule
# Creates or updates .gitmodules

cat .gitmodules
# [submodule "libs/shared"]
#     path = libs/shared
#     url = https://github.com/user/shared-library.git

Example 2 — Cloning a project that uses submodules:
git clone --recurse-submodules https://github.com/user/main-project.git
# Clones the main project AND initializes all submodules automatically

Example 3 — Manually initializing submodules after a plain clone:
git clone https://github.com/user/main-project.git
cd main-project
git submodule init
git submodule update
# Now the submodule directories are populated

Example 4 — Checking submodule status:
git submodule status
# -abc1234 libs/shared    ← minus sign means not initialized
#  abc1234 libs/shared    ← space means up to date
# +abc1234 libs/shared    ← plus sign means submodule is ahead of recorded commit

Example 5 — Updating the submodule to a newer version:
cd libs/shared
git pull origin main
cd ../..
git add libs/shared
git commit -m "Update shared-library submodule to include new API"

Example 6 — Updating all submodules at once:
git submodule update --remote --merge
# Fetches latest from each submodule's tracked branch and merges

Example 7 — Removing a submodule completely:
git submodule deinit libs/shared
git rm libs/shared
rm -rf .git/modules/libs/shared
git commit -m "Remove shared-library submodule"
"""

g7_key_points = """
- A submodule is a Git repository embedded inside another Git repository
- The parent repository stores a reference to a specific commit in the submodule — not its files
- .gitmodules lists all submodules with their paths and remote URLs
- Cloning a repo with submodules requires --recurse-submodules or manual git submodule init and update
- Submodules are pinned to exact commits — they do not follow a branch automatically
- git submodule status shows whether submodules are initialized, up to date, or ahead of the recorded commit
- Updating a submodule requires pulling inside the submodule directory, then staging and committing the pointer change in the parent
- git submodule update --remote fetches the latest from each submodule's tracked branch
- Removing a submodule requires deinit, git rm, and manual cleanup of .git/modules
- Submodules prevent accidental drift — dependency updates are explicit and intentional
- The biggest practical challenge of submodules is that team members often forget to update them after pulling the parent
"""

g7_misconceptions = """
- "A submodule copies the external repository's files into the parent" — The parent only stores a pointer to a specific commit in the submodule. The actual files live in the submodule's own repository.
- "Pulling the parent automatically updates the submodule" — Pulling the parent only updates the recorded commit pointer. You must run git submodule update to actually update the submodule files.
- "Submodules track a branch, like main" — By default, a submodule is pinned to a specific commit hash, not a branch. It only moves to a new commit when you explicitly update it.
- "git clone gets the submodule content automatically" — A plain git clone does not populate submodule directories. You need --recurse-submodules during clone or git submodule init and update afterward.
- "Submodules are the only way to share code between repositories" — Alternatives include package managers (npm, pip, cargo), Git subtrees, and monorepos. Submodules are one tool, not the only option.
- "Deleting the submodule directory removes it from the repository" — Deleting the directory leaves stale entries in .gitmodules and .git/config. Proper removal requires git submodule deinit, git rm, and .git/modules cleanup.
"""

g7_real_world_use = """
- Large C and C++ projects use submodules to embed third-party libraries at a known stable version
- Game engines use submodules to include rendering libraries, physics engines, and tooling as version-pinned dependencies
- Firmware and embedded projects use submodules for hardware abstraction layers maintained by separate teams
- Documentation sites embed theme repositories as submodules to control exactly which version of the theme is used
- Monorepo alternatives sometimes use submodules to link individual service repositories under a common parent
- DevOps tooling repositories use submodules to reference configuration or script libraries maintained in separate repositories
"""

g7_next_concept_link = """
Submodules complete the Git knowledge graph. You now have a full picture from the fundamentals of version control through repositories, commits, branching, merging, history rewriting, and managing external dependencies. The next subject in your curriculum is SQL — starting with Database Basics, which covers how relational databases are structured and how data is organized before you query it.
"""

# ============================================================
# DATABASE INSERT — ALL CONCEPTS
# ============================================================

def insert_concept(cursor, concept_id, topic, base_content, examples,
                   key_points, misconceptions, real_world_use, next_concept_link):
    cursor.execute("""
        INSERT INTO concept_resources (
            concept_id, topic, base_content, examples,
            key_points, misconceptions, real_world_use, next_concept_link
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(concept_id) DO UPDATE SET
            topic             = excluded.topic,
            base_content      = excluded.base_content,
            examples          = excluded.examples,
            key_points        = excluded.key_points,
            misconceptions    = excluded.misconceptions,
            real_world_use    = excluded.real_world_use,
            next_concept_link = excluded.next_concept_link
    """, (
        concept_id, topic,
        base_content.strip(), examples.strip(),
        key_points.strip(), misconceptions.strip(),
        real_world_use.strip(), next_concept_link.strip()
    ))
    print(f"Success — concept '{concept_id}: {topic}' inserted or updated.")


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create table first
create_concept_resources_table(cursor)

# Then insert concepts
insert_concept(cursor, g1_id, g1_topic, g1_base_content, g1_examples,
               g1_key_points, g1_misconceptions, g1_real_world_use, g1_next_concept_link)

insert_concept(cursor, g2_id, g2_topic, g2_base_content, g2_examples,
               g2_key_points, g2_misconceptions, g2_real_world_use, g2_next_concept_link)

insert_concept(cursor, g3_id, g3_topic, g3_base_content, g3_examples,
               g3_key_points, g3_misconceptions, g3_real_world_use, g3_next_concept_link)

insert_concept(cursor, g4_id, g4_topic, g4_base_content, g4_examples,
               g4_key_points, g4_misconceptions, g4_real_world_use, g4_next_concept_link)

insert_concept(cursor, g5_id, g5_topic, g5_base_content, g5_examples,
               g5_key_points, g5_misconceptions, g5_real_world_use, g5_next_concept_link)

insert_concept(cursor, g6_id, g6_topic, g6_base_content, g6_examples,
               g6_key_points, g6_misconceptions, g6_real_world_use, g6_next_concept_link)

insert_concept(cursor, g7_id, g7_topic, g7_base_content, g7_examples,
               g7_key_points, g7_misconceptions, g7_real_world_use, g7_next_concept_link)

conn.commit()
conn.close()

print("\nAll Git concepts G1–G7 inserted successfully into git.db")
