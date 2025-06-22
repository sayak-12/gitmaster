import typer
from gitmaster.auth import keymanager
from gitmaster.auth import github
from tqdm import tqdm
import os
from gitmaster.loader import repo_loader
from gitmaster.embed.splitter import chunk_repo
from gitmaster.embed.embedder import embed_with_local_model
from gitmaster.db.vector_store import VectorStore
from gitmaster.rag.agent import answer_question, summarize_repo
import shutil
import importlib.metadata

# Get version from package metadata
try:
    __version__ = importlib.metadata.version("gitmaster")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"

def version_callback(value: bool):
    if value:
        typer.echo(f"gitmaster version {__version__}")
        raise typer.Exit()

app = typer.Typer(help="gitmaster - AI for your code repos")
repo_path = None

@app.callback()
def main(
    version: bool = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit")
):
    """gitmaster - AI for your code repos"""
    pass

@app.command()
def load(
    path_or_url: str,
    type: str = typer.Option("repo", help="repo or local"),
    clear_index: bool = typer.Option(False, "--clear-index", "-c", help="Clear existing vector index before indexing")
):
    """Load a GitHub or local repo into vector DB."""
    global repo_path
    try:
        typer.echo("🔄 Loading repo...")
        if type == "repo":
            repo_path = repo_loader.clone_repo(path_or_url)
        elif type == "local":
            repo_path = repo_loader.load_local_repo(path_or_url)
        else:
            raise ValueError("Type must be either 'repo' or 'local'.")

        typer.echo(f"📁 Repo ready at: {repo_path}")

        # Use repo folder name as identifier for index persistence
        repo_identifier = os.path.basename(repo_path.rstrip(os.sep))

        # Step 1: Chunk repo with progress bar
        typer.echo("🧩 Chunking code...")
        chunks = []
        for chunk in tqdm(chunk_repo(repo_path), desc="Chunking", unit="chunk"):
            chunks.append(chunk)

        if not chunks:
            typer.echo("⚠️ No valid code chunks found.")
            return

        # Step 2: Embed with progress bar
        typer.echo(f"🧠 Embedding {len(chunks)} chunks...")
        texts = [chunk["content"] for chunk in chunks]

        # We embed in batches, show progress
        batch_size = 16
        embeddings = []
        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding", unit="batch"):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = embed_with_local_model(batch_texts)
            embeddings.extend(batch_embeddings)

        # Step 3: Save to vector store, per-repo index
        store = VectorStore(repo_identifier=repo_identifier)

        if clear_index:
            typer.echo("🧹 Clearing existing vector index...")
            store.clear()

        # Fix metadata to be a dictionary
        metadata_list = []
        for chunk in chunks:
            metadata_str = chunk["metadata"]
            file_path, chunk_info = metadata_str.split(" (chunk ")
            chunk_num = int(chunk_info.rstrip(")"))
            metadata = {
                "file": file_path,
                "chunk": chunk_num,
                "content": chunk["content"],
                "start_line": (chunk_num - 1) * 10 + 1,  # Estimate, adjust based on chunking logic
                "end_line": chunk_num * 10  # Estimate, adjust based on chunking logic
            }
            metadata_list.append(metadata)

        store.add(embeddings, metadata_list)
        store.save()

        typer.echo("✅ Repo indexed and ready for questions.")
        with open("last_repo.txt", "w") as f:
            f.write(repo_path)

    except Exception as e:
        typer.echo(f"❌ Error loading repo: {e.__class__.__name__}: {str(e)}")

@app.command()
def ask(question: str):
    """Ask a question about the last loaded repo."""
    try:
        with open("last_repo.txt", "r") as f:
            repo_path = f.read().strip()
    except FileNotFoundError:
        typer.echo("❌ No repo loaded yet. Use `gitmaster load` first.")
        return

    repo_id = os.path.basename(repo_path.rstrip(os.sep))
    typer.echo(f"💬 Asking: {question}")
    answer = answer_question(question, repo_id, repo_path)
    typer.echo("\n🧠 Answer:\n" + answer)

@app.command()
def login():
    """Login to GitHub (for private repo access)."""
    try:
        typer.echo("Opening GitHub login...")
        github.login()
        typer.echo("Logged in to GitHub successfully.")
    except Exception as e:
        typer.echo(f"GitHub login failed: {e.__class__.__name__}")

@app.command()
def logout():
    """Logout of GitHub and clear API key."""
    try:
        typer.echo("🔒 Logging out...")
        keymanager.delete_all_keys()
        github.logout()
        typer.echo("✅ All credentials cleared.")
    except Exception as e:
        typer.echo(f"❌ Error logging out: {e.__class__.__name__}")

@app.command("change-key")
def change_key():
    """Set or update your API keys for different AI services."""
    try:
        typer.echo("🔑 API Key Management")
        typer.echo("Choose which API key to set:")
        typer.echo("1. OpenAI API Key")
        typer.echo("2. Gemini API Key")
        typer.echo("3. Anthropic API Key")
        typer.echo("4. View current keys")
        typer.echo("5. Set default key")
        typer.echo("6. Delete all keys")
        
        choice = typer.prompt("Enter your choice (1-6)", type=int)
        
        if choice == 1:
            key = typer.prompt("🔑 Enter your OpenAI API key", hide_input=True)
            keymanager.save_openai_key(key)
            typer.echo("✅ OpenAI API key saved securely.")
        elif choice == 2:
            key = typer.prompt("🔑 Enter your Gemini API key", hide_input=True)
            keymanager.save_gemini_key(key)
            typer.echo("✅ Gemini API key saved securely.")
        elif choice == 3:
            key = typer.prompt("🔑 Enter your Anthropic API key", hide_input=True)
            keymanager.save_anthropic_key(key)
            typer.echo("✅ Anthropic API key saved securely.")
        elif choice == 4:
            keys = keymanager.get_all_keys()
            default_service = keymanager.get_default_service()
            typer.echo("\n📋 Current API Keys:")
            for service, key in keys.items():
                status = "✅ Set" if key else "❌ Not set"
                default_indicator = " (Default)" if service == default_service else ""
                typer.echo(f"  {service.title()}: {status}{default_indicator}")
        elif choice == 5:
            keys = keymanager.get_all_keys()
            available_keys = [service for service, key in keys.items() if key]
            
            if not available_keys:
                typer.echo("❌ No API keys found. Please add at least one key first.")
                return
            
            if len(available_keys) == 1:
                typer.echo(f"ℹ️ Only one key available ({available_keys[0]}), it's already the default.")
                return
            
            typer.echo("Choose which key to set as default:")
            for i, service in enumerate(available_keys, 1):
                typer.echo(f"{i}. {service.title()}")
            
            try:
                key_choice = typer.prompt(f"Enter your choice (1-{len(available_keys)})", type=int)
                if 1 <= key_choice <= len(available_keys):
                    selected_service = available_keys[key_choice - 1]
                    keymanager.set_default_key(selected_service)
                    typer.echo(f"✅ {selected_service.title()} set as default key.")
                else:
                    typer.echo("❌ Invalid choice.")
            except ValueError:
                typer.echo("❌ Invalid input. Please enter a number.")
        elif choice == 6:
            confirm = typer.confirm("⚠️ Are you sure you want to delete all API keys?")
            if confirm:
                keymanager.delete_all_keys()
                typer.echo("✅ All API keys deleted.")
            else:
                typer.echo("❌ Operation cancelled.")
        else:
            typer.echo("❌ Invalid choice. Please select 1-6.")
            
    except Exception as e:
        typer.echo(f"❌ Error managing API keys: {e.__class__.__name__}")

@app.command()
def summarize():
    """Summarize the contents of the last loaded repository."""
    try:
        with open("last_repo.txt", "r") as f:
            repo_path = f.read().strip()
    except FileNotFoundError:
        typer.echo("❌ No repo loaded yet. Use `gitmaster load` first.")
        return

    repo_id = os.path.basename(repo_path.rstrip(os.sep))
    typer.echo(f"📝 Summarizing repository: {repo_id}")
    summary = summarize_repo(repo_id, repo_path)
    typer.echo("\n📖 Repository Summary:\n" + summary)

@app.command()
def clear():
    """Delete all temporary repo clones starting with 'gitmaster' and clear/delete all vector stores."""
    try:
        # Step 1: Delete temporary repo clones
        temp_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp")
        deleted_repos = 0
        if os.path.exists(temp_dir):
            for item in os.listdir(temp_dir):
                if item.startswith("gitmaster"):
                    item_path = os.path.join(temp_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)
                        deleted_repos += 1
                        typer.echo(f"🗑️ Deleted temporary repo: {item_path}")
        else:
            typer.echo("⚠️ Temp directory not found.")

        # Step 2: Clear and delete vector stores
        data_dir = "data"
        deleted_stores = 0
        if os.path.exists(data_dir):
            for item in os.listdir(data_dir):
                item_path = os.path.join(data_dir, item)
                if os.path.isdir(item_path):
                    # Initialize VectorStore to clear it
                    store = VectorStore(repo_identifier=item)
                    store.clear()
                    # Delete the directory and its contents
                    shutil.rmtree(item_path, ignore_errors=True)
                    deleted_stores += 1
                    typer.echo(f"🧹 Cleared and deleted vector store: {item_path}")
        else:
            typer.echo("⚠️ Data directory not found.")

        # Step 3: Delete last_repo.txt if it exists
        last_repo_file = "last_repo.txt"
        if os.path.exists(last_repo_file):
            os.remove(last_repo_file)
            typer.echo(f"🗑️ Deleted last_repo.txt")

        typer.echo(f"✅ Cleanup complete: {deleted_repos} repo(s) and {deleted_stores} vector store(s) removed.")
    except Exception as e:
        typer.echo(f"❌ Error during cleanup: {e.__class__.__name__}: {str(e)}")

@app.command()
def explain(file_path: str):
    """Explain a file in the loaded repository."""
    global repo_path
    typer.echo(f"🔍 Explaining repo: {repo_path}")
    # Try to get repo_path from global or last_repo.txt
    if not repo_path:
        try:
            with open("last_repo.txt", "r") as f:
                repo_path_local = f.read().strip()
                repo_path = repo_path_local
                typer.echo(f"Using repo from last load: {repo_path}")
        except FileNotFoundError:
            typer.echo("❌ No repo loaded yet. Use `gitmaster load` first.")
            return
    if not repo_path:
        typer.echo("❌ No repo loaded yet. Use `gitmaster load` first.")
        return
    # Remove leading slashes to avoid absolute path issues
    file_path = file_path.lstrip("/\\")
    abs_file_path = os.path.join(repo_path, file_path)
    if not os.path.isfile(abs_file_path):
        typer.echo(f"❌ File not found: {abs_file_path}")
        return
    try:
        with open(abs_file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
    except Exception as e:
        typer.echo(f"❌ Could not read file: {e}")
        return
    from gitmaster.rag.agent import get_explanation
    typer.echo(f"📝 Explaining {file_path}...")
    typer.echo(f"📂 File content:\n{file_content[:500]}...")
    explanation = get_explanation(file_content, file_path)
    typer.echo("\n🤖 Explanation:\n" + explanation)

@app.command()
def suggest(file_path: str):
    """Suggest improvements for a file in the loaded repository."""
    global repo_path
    typer.echo(f"🔍 Suggesting for repo: {repo_path}")
    # Try to get repo_path from global or last_repo.txt
    if not repo_path:
        try:
            with open("last_repo.txt", "r") as f:
                repo_path_local = f.read().strip()
                repo_path = repo_path_local
                typer.echo(f"Using repo from last load: {repo_path}")
        except FileNotFoundError:
            typer.echo("❌ No repo loaded yet. Use `gitmaster load` first.")
            return
    if not repo_path:
        typer.echo("❌ No repo loaded yet. Use `gitmaster load` first.")
        return
    # Remove leading slashes to avoid absolute path issues
    file_path = file_path.lstrip("/\\")
    abs_file_path = os.path.join(repo_path, file_path)
    if not os.path.isfile(abs_file_path):
        typer.echo(f"❌ File not found: {abs_file_path}")
        return
    try:
        with open(abs_file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
    except Exception as e:
        typer.echo(f"❌ Could not read file: {e}")
        return
    from gitmaster.rag.agent import get_suggestions
    typer.echo(f"📝 Suggesting improvements for {file_path}...")
    suggestions = get_suggestions(file_content, file_path)
    typer.echo("\n💡 Suggestions:\n" + suggestions)

@app.command()
def review_pr(pr_url: str):
    """Review a GitHub Pull Request and provide analysis using LLM."""
    try:
        typer.echo("🔍 Analyzing Pull Request...")
        
        # Parse PR URL and extract data
        from gitmaster.pr_reviewer import PRReviewer
        reviewer = PRReviewer()
        
        # Get PR data
        pr_data = reviewer.get_pr_data(pr_url)
        if not pr_data:
            typer.echo("❌ Could not fetch PR data. Check URL and permissions.")
            return
            
        # Show PR overview
        typer.echo(f"\n📋 PR: {pr_data['title']}")
        typer.echo(f"👤 Author: {pr_data['author']}")
        typer.echo(f"📅 Created: {pr_data['created_at']}")
        typer.echo(f"📁 Files changed: {len(pr_data['files'])}")
        typer.echo(f"➕ Additions: {pr_data['additions']}")
        typer.echo(f"➖ Deletions: {pr_data['deletions']}")
        
        # Show changed files
        typer.echo(f"\n📄 Changed Files:")
        for i, file_info in enumerate(pr_data['files'], 1):
            status = file_info['status']
            additions = file_info.get('additions', 0)
            deletions = file_info.get('deletions', 0)
            typer.echo(f"  {i}. {file_info['filename']} ({status})")
            if status != 'removed':
                typer.echo(f"     +{additions} -{deletions} lines")
        
        # Ask user if they want to analyze all files or select specific ones
        if len(pr_data['files']) > 10:
            typer.echo(f"\n⚠️ Large PR detected ({len(pr_data['files'])} files).")
            choice = typer.prompt(
                "Choose analysis mode",
                type=typer.Choice(['all', 'select'], case_sensitive=False),
                default='select'
            )
        else:
            choice = 'all'
        
        if choice == 'select':
            typer.echo("\nSelect files to analyze (comma-separated numbers, or 'all'):")
            selection = typer.prompt("File numbers")
            
            if selection.lower() == 'all':
                selected_files = pr_data['files']
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(',')]
                    selected_files = [pr_data['files'][i] for i in indices if 0 <= i < len(pr_data['files'])]
                except (ValueError, IndexError):
                    typer.echo("❌ Invalid selection. Analyzing all files.")
                    selected_files = pr_data['files']
        else:
            selected_files = pr_data['files']
        
        # Analyze the PR
        typer.echo(f"\n🧠 Analyzing {len(selected_files)} files...")
        analysis = reviewer.analyze_pr(pr_data, selected_files)
        
        typer.echo("\n" + "="*50)
        typer.echo("📊 PR ANALYSIS")
        typer.echo("="*50)
        typer.echo(analysis)
        
    except Exception as e:
        typer.echo(f"❌ Error reviewing PR: {e.__class__.__name__}: {str(e)}")

if __name__ == "__main__":
    app()
