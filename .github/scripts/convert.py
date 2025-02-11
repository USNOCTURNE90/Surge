import os
import requests

def get_repo_files(owner, repo, branch='main'):
    """Get all files from GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    response = requests.get(url)
    if response.status_code == 200:
        return [item['path'] for item in response.json()['tree'] 
                if item['type'] == 'blob' and 
                not item['path'].startswith('.')]
    return []

def get_raw_content(owner, repo, branch, file_path):
    """Get content from GitHub raw URL."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
    print(f"Fetching content from: {url}")
    response = requests.get(url)
    return response.text

def convert_line(line):
    """Convert a single line from Surge to Clash format."""
    if not line.strip():
        return line
        
    if line.strip().startswith('#'):
        return line.strip() + '\n'
        
    return line

def process_raw_content(content, output_path):
    """Process raw content and save to file."""
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
    
    # Write converted content
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(converted_lines)
    print(f"Saved to: {output_path}")

def main():
    """Main function to handle the conversion process."""
    owner = "USNOCTURNE"
    repo = "Surge"
    branch = "main"
    target_dir = os.getenv('TARGET_DIR', 'clash-repo')
    
    print(f"Getting files from {owner}/{repo}")
    files = get_repo_files(owner, repo, branch)
    print(f"Found files: {files}")
    
    # Process each file
    for file_path in files:
        print(f"\nProcessing file: {file_path}")
        content = get_raw_content(owner, repo, branch, file_path)
        output_path = os.path.join(target_dir, file_path)
        process_raw_content(content, output_path)

if __name__ == '__main__':
    main()
