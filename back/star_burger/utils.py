import os
from pathlib import Path


def get_current_git_branch():
    """Возвращает имя активной Git-ветки или None, если ветка не найдена."""
    git_dir = Path(__file__).resolve().parent / ".git"
    head_path = git_dir / "HEAD"

    if not head_path.exists():
        return None

    try:
        content = head_path.read_text(encoding="utf-8").strip()

        if content.startswith("ref: refs/heads/"):
            ref_path = content.split(":", 1)[1].strip()
            branch = os.path.basename(ref_path)
            return branch

        return content[:7]

    except (IOError, OSError):
        return None
