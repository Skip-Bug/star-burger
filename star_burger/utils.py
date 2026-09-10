from pathlib import Path


def get_current_git_branch():
    head_path = Path(__file__).resolve().parent / ".git" / "HEAD"
    if not head_path.exists():
        return None
    try:
        content = head_path.read_text(encoding="utf-8").strip()
        if content.startswith("ref: refs/heads/"):
            return content.replace("ref: refs/heads/", "")
        return None
    except (IOError, OSError):
        return None
