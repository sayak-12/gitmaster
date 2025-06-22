import os
from typing import List, Tuple

# Folders to ignore
IGNORE_DIRS = {
    # Version control
    '.git', '.svn', '.hg',
    
    # Node.js
    'node_modules', 'npm-debug.log', 'yarn-error.log',
    
    # Python
    '__pycache__', '.pytest_cache', '.coverage', 'htmlcov',
    '.venv', 'venv', 'env', '.env', 'env.bak', 'venv.bak',
    '*.pyc', '*.pyo', '*.pyd', '.Python',
    
    # IDEs and editors
    '.idea', '.vscode', '.vs', '.sublime-project', '.sublime-workspace',
    '.vim', '.emacs.d', '.atom',
    
    # Build and dist
    'build', 'dist', 'target', 'out', 'bin', 'obj',
    '.gradle', '.mvn', 'gradle', 'maven',
    
    # Package managers
    '.npm', '.yarn', 'package-lock.json', 'yarn.lock',
    'pip-log.txt', 'pip-delete-this-directory.txt',
    
    # OS generated
    '.DS_Store', '.DS_Store?', '._*', '.Spotlight-V100', '.Trashes',
    'ehthumbs.db', 'Thumbs.db', 'desktop.ini',
    
    # Logs and temp
    'logs', '*.log', 'tmp', 'temp', '.tmp', '.temp',
    
    # Cache and data
    '.cache', 'cache', '.data', 'data',
    
    # Docker
    '.dockerignore', 'Dockerfile', 'docker-compose.yml',
    
    # CI/CD
    '.github', '.gitlab-ci.yml', '.travis.yml', '.circleci',
    
    # Documentation build
    'docs/_build', 'site', '_site', '.sass-cache',
    
    # Database
    '*.db', '*.sqlite', '*.sqlite3',
    
    # Archives
    '*.zip', '*.tar.gz', '*.rar', '*.7z',
    
    # Images and media
    '*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.svg',
    '*.mp4', '*.avi', '*.mov', '*.wmv', '*.flv',
    '*.mp3', '*.wav', '*.flac', '*.aac',
    
    # Documents
    '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx',
    '*.ppt', '*.pptx', '*.odt', '*.ods', '*.odp',
    
    # Executables
    '*.exe', '*.dll', '*.so', '*.dylib', '*.app',
    
    # Backup files
    '*.bak', '*.backup', '*.old', '*.orig',
    
    # Lock files
    '*.lock', '.lock',
    
    # Environment and config
    '.env.local', '.env.development', '.env.test', '.env.production',
    'config.local.js', 'config.local.json',
    
    # Testing
    'coverage', '.nyc_output', 'test-results', 'playwright-report',
    
    # Misc
    '.gitignore', '.gitattributes', 'README.md', 'LICENSE',
    'CHANGELOG.md', 'CONTRIBUTING.md', 'CODE_OF_CONDUCT.md'
}

# File extensions to ignore
IGNORE_EXTENSIONS = {
    '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
    '.exe', '.bin', '.obj', '.o', '.a',
    '.zip', '.tar.gz', '.rar', '.7z',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
    '.mp4', '.avi', '.mov', '.wmv', '.flv',
    '.mp3', '.wav', '.flac', '.aac',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.ppt', '.pptx', '.odt', '.ods', '.odp',
    '.db', '.sqlite', '.sqlite3',
    '.bak', '.backup', '.old', '.orig',
    '.lock'
}

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
    """Check if a file or directory should be ignored."""
    parts = file_path.split(os.sep)
    
    # Check if any directory in the path matches ignore patterns
    for part in parts:
        if part in IGNORE_DIRS:
            return True
        # Check for wildcard patterns (e.g., *.pyc)
        for pattern in IGNORE_DIRS:
            if pattern.startswith('*') and part.endswith(pattern[1:]):
                return True
    
    # Check file extension
    _, ext = os.path.splitext(file_path)
    if ext.lower() in IGNORE_EXTENSIONS:
        return True
    
    return False


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
    processed_files = 0
    ignored_files = 0

    for root, dirs, files in os.walk(repo_path):
        # Filter ignored directories from dirs list to prevent walking into them
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not should_ignore(os.path.join(root, d))]

        for file in files:
            file_path = os.path.join(root, file)

            if should_ignore(file_path):
                ignored_files += 1
                continue

            if os.path.getsize(file_path) > MAX_FILE_SIZE:
                ignored_files += 1
                continue

            if is_binary_file(file_path):
                ignored_files += 1
                continue

            content = read_file_safe(file_path)
            if not content.strip():
                ignored_files += 1
                continue

            chunks = chunk_lines(content)
            rel_path = os.path.relpath(file_path, repo_path)
            processed_files += 1

            for i, chunk in enumerate(chunks):
                metadata = f"{rel_path} (chunk {i+1})"
                all_chunks.append({"content": chunk, "metadata": metadata})

    print(f"📁 Processed {processed_files} files, ignored {ignored_files} files")
    return all_chunks