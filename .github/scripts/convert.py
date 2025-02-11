import os
import requests
import json

def get_repo_files(owner, repo, branch='main'):
    """Get all files from GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    print(f"Fetching repo contents from: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for bad status codes
        
        data = response.json()
        print(f"API Response: {json.dumps(data, indent=2)}")
        
        files = [item['path'] for item in data['tree'] 
                if item['type'] == 'blob' and 
                not item['path'].startswith('.')]
        
        print(f"Found files: {files}")
        return files
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching repo contents: {e}")
        if response := getattr(e, 'response', None):
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        return []

def get_raw_content(owner, repo, branch, file_path):
    """Get content from GitHub raw URL."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
    print(f"Fetching content from: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching file content: {e}")
        if response := getattr(e, 'response', None):
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        return None

def convert_line(line):
    """Convert a single line from Surge to Clash format."""
    if not line.strip():
        return line
    
    if line.strip().startswith('#'):
        return line.strip() + '\n'
    
    return line

def process_raw_content(content, output_path):
    """Process raw content and save to file."""
    if content is None:
        print(f"Skipping {output_path} due to empty content")
        return
    
    # Convert line by line
    converted_lines = []
    for line in content.splitlines(True):
        converted_line = convert_line(line)
        converted_lines.append(converted_line)
    
    # Add rules: at the beginning if file is not empty
    if ''.join(converted_lines).strip():
        converted_lines.insert(0, 'rules:\n')
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # Write converted content
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(converted_lines)
        print(f"Successfully saved to: {output_path}")
    except IOError as e:
        print(f"Error writing file {output_path}: {e}")

def main():
    """Main function to handle the conversion process."""
    owner = "USNOCTURNE90"  # 修改为你的 GitHub 用户名
    repo = "Surge"
    branch = "main"
    target_dir = os.getenv('TARGET_DIR', 'clash-repo')
    
    print(f"\n=== Starting Conversion Process ===")
    print(f"Owner: {owner}")
    print(f"Repo: {repo}")
    print(f"Branch: {branch}")
    print(f"Target Directory: {target_dir}")
    
    files = get_repo_files(owner, repo, branch)
    if not files:
        print("No files found or error occurred while fetching files")
        return 1
    
    success = True
    for file_path in files:
        print(f"\n--- Processing {file_path} ---")
        content = get_raw_content(owner, repo, branch, file_path)
        if content is None:
            success = False
            continue
            
        output_path = os.path.join(target_dir, file_path)
        process_raw_content(content, output_path)
    
    return 0 if success else 1

if __name__ == '__main__':
    exit(main())
