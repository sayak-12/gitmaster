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

app = typer.Typer(help="gitmaster - AI for your code repos")


@app.command()
def load(
    path_or_url: str,
    type: str = typer.Option("repo", help="repo or local"),
    clear_index: bool = typer.Option(False, "--clear-index", "-c", help="Clear existing vector index before indexing")
):
    """Load a GitHub or local repo into vector DB."""
    try:
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
        keymanager.delete_openai_key()
        github.logout()
        typer.echo("✅ All credentials cleared.")
    except Exception as e:
        typer.echo(f"❌ Error logging out: {e.__class__.__name__}")


@app.command("change-key")
def change_key():
    """Set or update your OpenAI API key."""
    try:
        key = typer.prompt("🔑 Enter your OpenAI API key", hide_input=True)
        keymanager.save_openai_key(key)
        typer.echo("✅ API key saved securely.")
    except Exception as e:
        typer.echo(f"❌ Error saving API key: {e.__class__.__name__}")


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
if __name__ == "__main__":
    app()
