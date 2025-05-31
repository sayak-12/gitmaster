# GitMaster

GitMaster is an AI-powered CLI tool designed to help users interact with GitHub or local repositories. It leverages Retrieval-Augmented Generation (RAG) and Large Language Models (LLMs) to answer questions about codebases, summarize repositories, and more.

## Features

- Load and index GitHub or local repositories.
- Ask questions about the last loaded repository.
- Summarize the contents of a repository.
- Manage authentication for GitHub and OpenAI.
- Clear temporary data and vector stores.

## Installation from PyPI

To install GitMaster from PyPI, follow these steps:

1. Install GitMaster using pip:
   ```bash
   pip install gitmaster
   ```

2. Set up your OpenAI API key:
   ```bash
   gitmaster change-key
   ```

## Commands

Below is a list of all available commands in GitMaster:

### `gitmaster load`
Load a GitHub or local repository into the vector database.

#### Options:
- `path_or_url`: Path to a local repository or URL of a GitHub repository.
- `--type`: Specify `repo` for GitHub repositories or `local` for local repositories (default: `repo`).
- `--clear-index` / `-c`: Clear existing vector index before indexing.

#### Example:
```bash
gitmaster load https://github.com/yourusername/yourrepo --type repo
```

### `gitmaster ask`
Ask a question about the last loaded repository.

#### Example:
```bash
gitmaster ask "What does the main function do?"
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
Set or update your OpenAI API key.

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
- OpenAI API key (for LLM-based features, optional)
- Git installed on your system

## License

This project is licensed under the MIT License.

## Authors

Sayak Raha  @sayak-12
sayakraha12@gmail.com

Senjuti Saha @shuamamine
sahasenjuti796@gmail.com