import re
import requests
from urllib.parse import urlparse
from typing import Dict, List, Optional
from gitmaster.auth.github import get_token
from gitmaster.auth.keymanager import get_default_service
from gitmaster.rag.agent import get_llm_response

class PRReviewer:
    def __init__(self):
        self.token = get_token()
        self.api_base = "https://api.github.com"
        
    def parse_pr_url(self, pr_url: str) -> Optional[Dict[str, str]]:
        """Parse GitHub PR URL to extract owner, repo, and PR number."""
        # Handle different GitHub PR URL formats
        patterns = [
            r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)',
            r'https://github\.com/([^/]+)/([^/]+)/compare/([^?]+)',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, pr_url)
            if match:
                if 'pull' in pr_url:
                    return {
                        'owner': match.group(1),
                        'repo': match.group(2),
                        'pr_number': match.group(3)
                    }
                else:
                    # For compare URLs, we need to extract PR number differently
                    # This is a simplified approach
                    return None
        
        return None
    
    def get_pr_data(self, pr_url: str) -> Optional[Dict]:
        """Fetch PR data from GitHub API."""
        parsed = self.parse_pr_url(pr_url)
        if not parsed:
            raise ValueError("Invalid GitHub PR URL format")
        
        if not self.token:
            raise ValueError("GitHub token required. Use 'gitmaster login' first.")
        
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get PR details
        pr_url_api = f"{self.api_base}/repos/{parsed['owner']}/{parsed['repo']}/pulls/{parsed['pr_number']}"
        response = requests.get(pr_url_api, headers=headers)
        
        if response.status_code == 404:
            raise ValueError("PR not found or not accessible. Check URL and permissions.")
        elif response.status_code != 200:
            raise ValueError(f"GitHub API error: {response.status_code}")
        
        pr_data = response.json()
        
        # Get PR files
        files_url = f"{pr_url_api}/files"
        files_response = requests.get(files_url, headers=headers)
        
        if files_response.status_code != 200:
            raise ValueError(f"Could not fetch PR files: {files_response.status_code}")
        
        files_data = files_response.json()
        
        # Process and filter files
        processed_files = []
        total_additions = 0
        total_deletions = 0
        
        for file_info in files_data:
            # Skip files that are too large or binary
            if file_info.get('size', 0) > 100 * 1024:  # 100KB limit
                continue
                
            if file_info.get('binary', False):
                continue
            
            # Get file extension
            filename = file_info['filename']
            if '.' in filename:
                ext = filename.split('.')[-1].lower()
                # Skip certain file types
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'svg', 'ico', 'pdf', 'zip', 'tar', 'gz']:
                    continue
            
            processed_files.append({
                'filename': filename,
                'status': file_info['status'],
                'additions': file_info.get('additions', 0),
                'deletions': file_info.get('deletions', 0),
                'changes': file_info.get('changes', 0),
                'patch': file_info.get('patch', ''),
                'raw_url': file_info.get('contents_url', '')
            })
            
            total_additions += file_info.get('additions', 0)
            total_deletions += file_info.get('deletions', 0)
        
        return {
            'title': pr_data['title'],
            'description': pr_data.get('body', ''),
            'author': pr_data['user']['login'],
            'created_at': pr_data['created_at'],
            'state': pr_data['state'],
            'files': processed_files,
            'additions': total_additions,
            'deletions': total_deletions,
            'total_changes': total_additions + total_deletions
        }
    
    def analyze_pr(self, pr_data: Dict, selected_files: List[Dict]) -> str:
        """Analyze PR using LLM with token management."""
        
        # Build context for LLM
        context = self._build_analysis_context(pr_data, selected_files)
        
        # Check token limits and truncate if necessary
        context = self._truncate_context(context)
        
        # Create analysis prompt
        prompt = self._create_analysis_prompt(pr_data, context)
        
        # Get LLM response
        try:
            response = get_llm_response(prompt)
            return response
        except Exception as e:
            return f"❌ Error during analysis: {str(e)}"
    
    def _build_analysis_context(self, pr_data: Dict, selected_files: List[Dict]) -> str:
        """Build context string from PR data and selected files."""
        context_parts = []
        
        # Add PR metadata
        context_parts.append(f"PR Title: {pr_data['title']}")
        if pr_data.get('description'):
            context_parts.append(f"Description: {pr_data['description']}")
        context_parts.append(f"Author: {pr_data['author']}")
        context_parts.append(f"State: {pr_data['state']}")
        context_parts.append(f"Files changed: {len(selected_files)}")
        context_parts.append(f"Total changes: +{pr_data['additions']} -{pr_data['deletions']} lines")
        
        # Add file changes
        context_parts.append("\nChanged Files:")
        for file_info in selected_files:
            context_parts.append(f"\nFile: {file_info['filename']}")
            context_parts.append(f"Status: {file_info['status']}")
            context_parts.append(f"Changes: +{file_info['additions']} -{file_info['deletions']} lines")
            
            # Add patch/diff if available and not too large
            if file_info.get('patch') and len(file_info['patch']) < 5000:
                context_parts.append("Diff:")
                context_parts.append(file_info['patch'])
            elif file_info.get('patch'):
                # Truncate large patches
                patch = file_info['patch'][:5000] + "\n... (truncated)"
                context_parts.append("Diff (truncated):")
                context_parts.append(patch)
        
        return "\n".join(context_parts)
    
    def _truncate_context(self, context: str, max_tokens: int = 8000) -> str:
        """Truncate context to stay within token limits."""
        # Rough estimation: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(context) <= max_chars:
            return context
        
        # Truncate and add note
        truncated = context[:max_chars]
        truncated += "\n\n... (context truncated due to size limits)"
        return truncated
    
    def _create_analysis_prompt(self, pr_data: Dict, context: str) -> str:
        """Create the analysis prompt for the LLM."""
        return f"""You are a senior software engineer reviewing a GitHub Pull Request. Please analyze the following PR and provide a comprehensive review.

{context}

Please provide your analysis in the following format:

## Summary
Brief overview of what this PR does and its main changes.

## Key Changes
- List the most important modifications
- Highlight architectural changes if any
- Note any new features or bug fixes

## Potential Issues
- Security concerns
- Performance implications
- Code quality issues
- Potential bugs or edge cases

## Suggestions for Improvement
- Code style suggestions
- Better approaches or alternatives
- Missing tests or documentation
- Performance optimizations

## Overall Assessment
- Risk level (Low/Medium/High)
- Whether this PR is ready to merge
- Any blocking issues that need to be addressed

## Recommendations
- Specific actionable feedback
- Priority of suggested changes

Be thorough but concise. Focus on the most important aspects that would affect code quality, maintainability, and functionality.""" 