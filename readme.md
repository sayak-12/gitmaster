# GitMaster

GitMaster is an AI-powered CLI tool designed to help users interact with GitHub or local repositories. It leverages Retrieval-Augmented Generation (RAG) and Large Language Models (LLMs) to answer questions about codebases, summarize repositories, review pull requests, and more.

## Features

- Load and index GitHub or local repositories with smart file filtering
- Ask questions about the last loaded repository
- Summarize the contents of a repository
- Review GitHub Pull Requests with AI analysis
- Support for multiple LLM providers (OpenAI, Google Gemini, Anthropic Claude)
- Manage authentication for GitHub and AI services
- Clear temporary data and vector stores
- Explain and suggest improvements for specific files

## Installation from PyPI

To install GitMaster from PyPI, follow these steps:

1. Install GitMaster using pip:
   ```bash
   pip install gitmaster
   ```

2. Set up your AI service API key:
   ```bash
   gitmaster change-key
   ```

## Commands

Below is a list of all available commands in GitMaster:

### `gitmaster --version` / `gitmaster -v`
Display the current version of GitMaster.

### `gitmaster load`
Load a GitHub or local repository into the vector database.

#### Options:
- `path_or_url`: Path to a local repository or URL of a GitHub repository.
- `--type`: Specify `repo` for GitHub repositories or `local` for local repositories (default: `repo`).
- `--clear-index` / `-c`: Clear existing vector index before indexing.

#### Example:
```bash
gitmaster load https://github.com/yourusername/yourrepo --type repo
gitmaster load . --type local
```

### `gitmaster ask`
Ask a question about the last loaded repository.

#### Example:
```bash
gitmaster ask "What does the main function do?"
```

### `gitmaster review-pr`
Review a GitHub Pull Request and provide AI-powered analysis.

#### Example:
```bash
gitmaster review-pr https://github.com/owner/repo/pull/123
```

### `gitmaster explain`
Explain a specific file in the loaded repository.

#### Example:
```bash
gitmaster explain src/main.py
```

### `gitmaster suggest`
Get improvement suggestions for a specific file in the loaded repository.

#### Example:
```bash
gitmaster suggest src/main.py
```

### `gitmaster login`
Log in to GitHub for private repository access.

#### Example:
```bash
gitmaster login
```

### `gitmaster logout`
Log out of GitHub and clear stored credentials.

#### Example:
```bash
gitmaster logout
```

### `gitmaster change-key`
Set or update your AI service API keys and manage default settings.

#### Supported Services:
- OpenAI (GPT models)
- Google Gemini
- Anthropic Claude

#### Example:
```bash
gitmaster change-key
```

### `gitmaster summarize`
Summarize the contents of the last loaded repository.

#### Example:
```bash
gitmaster summarize
```

### `gitmaster clear`
Delete all temporary repository clones and clear vector stores.

#### Example:
```bash
gitmaster clear
```

## Usage

To see the help menu for GitMaster, run:
```bash
gitmaster --help
```

## Requirements

- Python 3.8 or higher
- AI service API key (OpenAI, Google Gemini, or Anthropic Claude)
- Git installed on your system

## Changelog

### Version 0.1.3 (Latest)
- **✨ New Features:**
  - Added support for multiple LLM providers (Google Gemini, Anthropic Claude)
  - Implemented `--version` / `-v` command to display current version
  - Added `review-pr` command for AI-powered Pull Request analysis
  - Added `explain` command to explain specific files
  - Added `suggest` command to get improvement suggestions for files
  - Implemented default LLM key selection system

- **🔧 Improvements:**
  - Enhanced file filtering system for local repository loading
  - Added comprehensive ignore patterns for common development artifacts:
    - Virtual environments (`.venv`, `venv`, `env`)
    - Build artifacts (`build`, `dist`, `__pycache__`)
    - Package managers (`node_modules`, `.npm`, `.yarn`)
    - IDE files (`.idea`, `.vscode`, `.vs`)
    - OS files (`.DS_Store`, `Thumbs.db`)
    - Logs and temp files (`logs`, `*.log`, `tmp`)
    - And many more development-related folders
  - Improved token management for large PRs
  - Better error handling for GitHub API access
  - Enhanced user interaction for file selection in large PRs

- **🐛 Bug Fixes:**
  - Fixed local repository loading getting stuck on large codebases
  - Improved file extension filtering
  - Better handling of binary files and large files

### Version 0.1.2
- Initial release with basic RAG functionality
- Support for OpenAI API
- GitHub and local repository loading
- Basic question answering and summarization

## License

This project is licensed under the MIT License.

## Authors

Sayak Raha  @sayak-12
sayakraha12@gmail.com

Senjuti Saha @shuamamine
sahasenjuti796@gmail.com