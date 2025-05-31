import os
from typing import List, Tuple

# Folders to ignore
IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', '.idea', '.vscode'}
MAX_FILE_SIZE = 100 * 1024  # 100 KB
CHUNK_SIZE = 40
OVERLAP = 10


def is_binary_file(filepath: str) -> bool:
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:
                return True
        return False
    except Exception:
        return True


def should_ignore(file_path: str) -> bool:
    parts = file_path.split(os.sep)
    return any(part in IGNORE_DIRS for part in parts)


def read_file_safe(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def chunk_lines(content: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> List[str]:
    lines = content.splitlines()
    chunks = []
    i = 0
    while i < len(lines):
        chunk = lines[i:i + chunk_size]
        if chunk:
            chunks.append("\n".join(chunk))
        i += chunk_size - overlap
    return chunks


def chunk_repo(repo_path: str) -> List[dict]:
    """
    Splits all valid files in a repo into chunks.
    Returns a list of dictionaries with 'content' and 'metadata' keys.
    """
    all_chunks = []

    for root, dirs, files in os.walk(repo_path):
        # Filter ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            file_path = os.path.join(root, file)

            if should_ignore(file_path):
                continue

            if os.path.getsize(file_path) > MAX_FILE_SIZE:
                continue

            if is_binary_file(file_path):
                continue

            content = read_file_safe(file_path)
            if not content.strip():
                continue

            chunks = chunk_lines(content)
            rel_path = os.path.relpath(file_path, repo_path)

            for i, chunk in enumerate(chunks):
                metadata = f"{rel_path} (chunk {i+1})"
                all_chunks.append({"content": chunk, "metadata": metadata})

    return all_chunks