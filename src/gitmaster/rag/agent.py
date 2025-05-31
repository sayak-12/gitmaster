import os
from typing import List, Dict
from gitmaster.embed.embedder import embed_with_local_model
from gitmaster.db.vector_store import VectorStore
from gitmaster.utils.network import is_online
from gitmaster.auth.keymanager import get_openai_key
from datetime import time 
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

def get_file_tree(repo_path: str) -> Dict[str, List[str]]:
    """
    Recursively build a file tree of the repository.
    Returns a dictionary with directories as keys and lists of files as values.
    """
    file_tree = {}
    for root, dirs, files in os.walk(repo_path):
        rel_dir = os.path.relpath(root, repo_path)
        if rel_dir == ".":
            rel_dir = "root"
        file_tree[rel_dir] = [f for f in files if os.path.isfile(os.path.join(root, f))]
    return file_tree

def format_file_tree(file_tree: Dict[str, List[str]]) -> str:
    """
    Format the file tree into a readable string for the prompt.
    """
    tree_str = "Repository File Tree:\n"
    for directory, files in file_tree.items():
        tree_str += f"\n{directory}/\n"
        for file in files:
            tree_str += f"  - {file}\n"
    return tree_str

def answer_question(question: str, repo_identifier: str, repo_path: str, k: int = 5) -> str:
    print("🔍 Processing your question...")

    # Step 1: Get the file tree
    file_tree = get_file_tree(repo_path)
    file_tree_str = format_file_tree(file_tree)

    # Step 2: Embed the query
    query_vec = embed_with_local_model([question])[0]

    # Step 3: Load relevant vector store
    store = VectorStore(repo_identifier)
    results = store.search(query_vec, k=k)

    # Step 4: Reconstruct context from vector search
    context_blocks = []
    for meta, _ in results:
        content = meta.get("content", "")
        file = meta.get("file", "unknown")
        lines = f"{meta.get('start_line', '?')}–{meta.get('end_line', '?')}"
        context_blocks.append(f"# {file}:{lines}\n{content}")
    context = "\n\n".join(context_blocks) if context_blocks else "No relevant code chunks found."

    # Step 5: Check if vector search yielded poor results
    poor_results = not results or all(dist > 1.0 for _, dist in results)  # Threshold for "poor" match

    # Step 6: Handle API key and connectivity
    api_key = get_openai_key()
    if not api_key or not is_online():
        msg = "⚠️ Offline or no OpenAI key. Here are relevant files:\n\n"
        if poor_results:
            msg += "No good vector matches found, but here’s the file tree:\n"
            msg += file_tree_str
        else:
            for meta, dist in results:
                filename = meta.get("file", "unknown")
                line_info = f"lines {meta.get('start_line', '?')}–{meta.get('end_line', '?')}"
                msg += f"• {filename} ({line_info})\n"
        return msg

    if OpenAI is None:
        return "❌ OpenAI SDK not installed. Run `pip install openai`."

    # Step 7: Query OpenAI with file tree and context
    system_prompt = "You are a code assistant helping the user understand a codebase."
    user_prompt = f"{system_prompt}\n\n{file_tree_str}\n\nContext from Vector Search:\n{context}\n\nQuestion: {question}"

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        answer = response.choices[0].message.content.strip()

        # Step 8: Fallback for poor vector results
        if poor_results and "no relevant results" in answer.lower():
            user_prompt_fallback = (
                f"{system_prompt}\n\n{file_tree_str}\n\n"
                f"Context: No relevant code chunks found in vector search.\n\n"
                f"Question: {question}"
            )
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt_fallback},
                ],
            )
            answer = response.choices[0].message.content.strip()
        return answer
    except Exception as e:
        return f"❌ OpenAI error: {str(e)}"

def summarize_repo(repo_identifier: str, repo_path: str) -> str:
    """Summarize the contents of the repository."""
    print("📝 Summarizing repository...")

    # Step 1: Get file tree
    file_tree = get_file_tree(repo_path)
    file_tree_str = format_file_tree(file_tree)

    # Step 2: Check API key and connectivity
    api_key = get_openai_key()
    if not api_key or not is_online():
        msg = "⚠️ Offline or no OpenAI key. Showing repository structure:\n\n"
        msg += file_tree_str
        return msg

    if OpenAI is None:
        return "❌ OpenAI SDK not installed. Run `pip install openai`."

    # Step 3: Search for README.md and read its content
    readme_content = "No README.md found in the repository."
    for root, _, files in os.walk(repo_path):
        if "README.md" in files:
            readme_path = os.path.join(root, "README.md")
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    readme_content = f.read().strip()
                readme_rel_path = os.path.relpath(readme_path, repo_path)
                readme_content = f"# {readme_rel_path}\n{readme_content}"
                break
            except Exception as e:
                readme_content = f"Error reading README.md: {str(e)}"

    # Step 4: Query OpenAI for summary
    system_prompt = "You are a code assistant helping the user understand a codebase."
    user_prompt = f"{system_prompt}\n\n{file_tree_str}\n\nREADME Content:\n{readme_content}\n\nTask: Provide a concise summary of the repository, including its structure, key files, and main purpose based on the file tree and README content."

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ OpenAI error: {str(e)}"

def get_explanation(file_content: str, file_path: str) -> str:
    """
    Get an LLM-based explanation for the given file content.
    Retries up to 3 times if a 500 Internal Server Error occurs.
    Output is formatted as plain text (no markdown decorations).
    """
    import traceback
    api_key = get_openai_key()
    if not api_key or not is_online():
        return "⚠️ Offline or no OpenAI key. Cannot provide explanation."
    if OpenAI is None:
        return "❌ OpenAI SDK not installed. Run `pip install openai`."
    system_prompt = "You are a code assistant. Explain the following code file in clear, concise language for a developer."
    user_prompt = f"Explain the file `{file_path}`.\n\nCode:\n\n{file_content}"
    client = OpenAI(api_key=api_key)
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            answer = response.choices[0].message.content.strip()
            # Remove markdown decorations from the output
            answer = answer.replace('**', '').replace('```', '')
            return answer
        except Exception as e:
            err_str = str(e)
            if ("500" in err_str or "Internal Server Error" in err_str) and attempt < max_retries:
                import time; time.sleep(2)
                continue
            if "500" in err_str or "Internal Server Error" in err_str:
                return "❌ OpenAI server error (500). Please try again later."
            traceback.print_exc()
            return f"❌ OpenAI error: {err_str}"

def get_suggestions(file_content: str, file_path: str) -> str:
    """
    Get LLM-based suggestions for improving the given file in terms of readability, performance, and structure.
    Retries up to 3 times if a 500 Internal Server Error occurs.
    Output is formatted as plain text (no markdown decorations).
    """
    import traceback
    api_key = get_openai_key()
    if not api_key or not is_online():
        return "⚠️ Offline or no OpenAI key. Cannot provide suggestions."
    if OpenAI is None:
        return "❌ OpenAI SDK not installed. Run `pip install openai`."
    system_prompt = "You are a code review assistant. Suggest improvements to the following code file in terms of readability, performance, and structure."
    user_prompt = f"Suggest improvements for the file `{file_path}`.\n\nCode:\n\n{file_content}"
    client = OpenAI(api_key=api_key)
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            answer = response.choices[0].message.content.strip()
            # Remove markdown decorations from the output
            answer = answer.replace('**', '').replace('```', '')
            return answer
        except Exception as e:
            err_str = str(e)
            if ("500" in err_str or "Internal Server Error" in err_str) and attempt < max_retries:
                import time; time.sleep(2)
                continue
            if "500" in err_str or "Internal Server Error" in err_str:
                return "❌ OpenAI server error (500). Please try again later."
            traceback.print_exc()
            return f"❌ OpenAI error: {err_str}"