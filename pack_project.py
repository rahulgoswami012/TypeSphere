import os

# Files and directories to ignore
IGNORE_DIRS = {'.git', 'venv', '.venv', '__pycache__', 'node_modules', '.idea', '.vscode'}
IGNORE_EXTS = {'.pyc', '.pyo', '.db', '.sqlite3', '.png', '.jpg', '.jpeg', '.svg', '.ico', '.woff', '.woff2', '.ttf'}
OUTPUT_FILE = 'typesphere_full_codebase.txt'

def pack():
    with open(OUTPUT_FILE, 'w', encoding='utf-8', errors='ignore') as out:
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for file in sorted(files):
                ext = os.path.splitext(file)[1].lower()
                if ext in IGNORE_EXTS or file == OUTPUT_FILE or file == 'pack_project.py':
                    continue
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, '.')
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    out.write(f"\n{'='*70}\n")
                    out.write(f"FILE: {rel_path}\n")
                    out.write(f"{'='*70}\n\n")
                    out.write(content)
                    out.write("\n")
                except Exception as e:
                    print(f"Skipping {rel_path}: {e}")
    print(f"Done! Created '{OUTPUT_FILE}'.")

if __name__ == '__main__':
    pack()