import os
import requests

def convert_line(line):
    """Convert a single line from Surge to Clash format."""
    if not line.strip():
        return line
    
    if line.strip().startswith('#'):
        return line.strip() + '\n'
    
    return line

def process_raw_content(content, output_path):
    """Process raw content and save to file."""
    print(f"Processing file: {output_path}")
    
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
    print(f"Successfully saved to: {output_path}")

def main():
    """Main function to handle the conversion process."""
    source_dir = '.'  # Current directory where the script runs
    target_dir = os.getenv('TARGET_DIR', 'clash-auto')
    
    print(f"\n=== Starting Conversion Process ===")
    print(f"Working directory: {os.getcwd()}")
    print(f"Source Directory: {source_dir}")
    print(f"Target Directory: {target_dir}")
    
    # List all files in source directory
    print("\nScanning for files...")
    for root, dirs, files in os.walk(source_dir):
        # Skip .git and .github directories
        if '.git' in root or '.github' in root:
            continue
            
        for file in files:
            if file.startswith('.') or file == 'readme.md' or file == 'LICENSE':
                continue
                
            source_path = os.path.join(root, file)
            # Calculate relative path from source directory
            rel_path = os.path.relpath(source_path, source_dir)
            target_path = os.path.join(target_dir, rel_path)
            
            print(f"\nFound file: {rel_path}")
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"File content length: {len(content)} bytes")
                process_raw_content(content, target_path)
            except Exception as e:
                print(f"Error processing {rel_path}: {e}")
                continue

if __name__ == '__main__':
    main()
