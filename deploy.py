"""
TypeSphere Universal Auto-Deploy & Git Synchronization Engine
Automatically stages, inspects, commits, and pushes any codebase updates to GitHub
to trigger Render production deployment.
"""

import os
import sys
import subprocess
from datetime import datetime, timezone, timedelta

# Indian Standard Time (IST, UTC+05:30) platform clock standard
IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def run_git_cmd(args, capture=True, check=True):
    """Executes a git CLI command safely and returns stdout."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=capture,
            text=True,
            check=check
        )
        return result.stdout.strip() if capture else ""
    except subprocess.CalledProcessError as e:
        if capture and e.stderr:
            print(f"⚠️ Git Warning/Error: {e.stderr.strip()}")
        raise


def get_current_branch():
    """Detects active git branch dynamically."""
    try:
        branch = run_git_cmd(["branch", "--show-current"])
        if branch:
            return branch
        # Fallback for detached or older git versions
        return run_git_cmd(["rev-parse", "--abbrev-ref", "HEAD"])
    except Exception:
        return "main"


def get_git_remote():
    """Finds primary remote repository name (defaulting to origin)."""
    try:
        remotes = run_git_cmd(["remote"]).split()
        return "origin" if "origin" in remotes else (remotes[0] if remotes else "origin")
    except Exception:
        return "origin"


def build_auto_commit_message():
    """Inspects staged/modified files and compiles a descriptive commit log."""
    now_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

    try:
        status_lines = run_git_cmd(["status", "--porcelain"]).splitlines()
    except Exception:
        status_lines = []

    if not status_lines:
        return f"chore: automated platform synchronization ({now_str})"

    modified_files = []
    for line in status_lines:
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            modified_files.append(parts[1])

    count = len(modified_files)
    sample_files = ", ".join(os.path.basename(f) for f in modified_files[:4])
    if count > 4:
        sample_files += f", +{count - 4} more"

    return f"update: {count} file(s) synchronized [{sample_files}] at {now_str}"


def deploy():
    print("\n" + "=" * 65)
    print("🚀 TypeSphere Universal Deployment Engine")
    print("=" * 65)

    # 1. Verify Git Repository
    try:
        run_git_cmd(["rev-parse", "--is-inside-work-tree"])
    except Exception:
        print("❌ Error: Current directory is not a Git repository.")
        sys.exit(1)

    # 2. Check for Working Tree Changes or Unpushed Commits
    status_raw = run_git_cmd(["status", "--porcelain"])
    branch = get_current_branch()
    remote = get_git_remote()

    # Check unpushed commits
    unpushed = ""
    try:
        unpushed = run_git_cmd(["log", f"{remote}/{branch}..HEAD", "--oneline"])
    except Exception:
        pass

    if not status_raw and not unpushed:
        print("\n✓ No changes detected. Repository is fully synchronized with remote.")
        print(f"  Branch: {branch} @ {remote}")
        print("=" * 65 + "\n")
        return

    # 3. Stage All Changes
    if status_raw:
        print("\n📦 Staging all codebase changes (new, modified, and deleted)...")
        run_git_cmd(["add", "-A"], capture=False)

        # 4. Determine Commit Message
        if len(sys.argv) > 1 and sys.argv[1].strip():
            commit_message = " ".join(sys.argv[1:]).strip()
        else:
            commit_message = build_auto_commit_message()

        print(f"📝 Committing: {commit_message}")
        try:
            run_git_cmd(["commit", "-m", commit_message], capture=False)
        except subprocess.CalledProcessError:
            print("⚠️ Commit step bypassed (no diff found after staging).")

    # 5. Push to Git Remote to Trigger Render Deployment
    print(f"\n📡 Pushing updates to {remote}/{branch}...")
    try:
        run_git_cmd(["push", remote, branch], capture=False)
        print("\n" + "=" * 65)
        print(f"✅ SUCCESS: Updates pushed to {remote}/{branch}!")
        print("   Render will now automatically detect the push and deploy.")
        print("=" * 65 + "\n")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Push failed: {e}")
        print("Tip: If upstream is missing, run: git push --set-upstream origin " + branch)
        sys.exit(1)


if __name__ == "__main__":
    deploy()