import os
import re

def convert_line(line):
    """Convert a single line from Surge to Clash format."""
    # Skip empty lines
    if not line.strip():
        return line
        
    # Handle comments
    if line.strip().startswith('#'):
        return line.strip() + '\n'
        
    # Skip lines that don't need conversion
    if not line.strip():
        return line
        
    # Convert Surge rule format to Clash format
    # The actual conversion logic remains the same as most formats are compatible
    return line

def process_file(input_path, output_path):
    """Process a single rule file."""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
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

def main():
    """Main function to handle the conversion process."""
    source_dir = os.getenv('SOURCE_DIR', 'surge')
    target_dir = os.getenv('TARGET_DIR', 'clash-repo')
    
    # Process all files in surge directory
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(('.list', '.conf')):  # Add other extensions if needed
                # Calculate relative path and create corresponding path in clash directory
                rel_path = os.path.relpath(os.path.join(root, file), source_dir)
                surge_path = os.path.join(root, file)
                clash_path = os.path.join(target_dir, rel_path)
                
                # Convert the file
                process_file(surge_path, clash_path)

if __name__ == '__main__':
    main()
