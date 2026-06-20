from pathlib import Path

ROOT = Path(".")

IGNORE = {".git", "__pycache__", ".idea", ".venv"}

def print_tree(path, indent=""):
    if path.name in IGNORE:
        return

    print(indent + path.name + ("/" if path.is_dir() else ""))

    if path.is_dir():
        for p in sorted(path.iterdir()):
            print_tree(p, indent + "    ")

print_tree(ROOT)