name: Convert Surge Rules to Clash

on:
  workflow_dispatch:

jobs:
  convert:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout Surge repository
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Create script
        run: |
          mkdir -p scripts
          cat > scripts/convert-rules.py << 'EOF'
import os
import re
from pathlib import Path

def convert_rule(line):
    if line.startswith('#') or not line.strip():
        return line, True
    
    rule_types = {
        'DOMAIN-SUFFIX': 'DOMAIN-SUFFIX',
        'DOMAIN': 'DOMAIN',
        'DOMAIN-KEYWORD': 'DOMAIN-KEYWORD',
        'IP-CIDR': 'IP-CIDR',
        'IP-CIDR6': 'IP-CIDR6',
        'PROCESS-NAME': None,
        'USER-AGENT': None,
    }
    
    parts = line.strip().split(',')
    if len(parts) < 2:
        return None, False
        
    rule_type = parts[0].upper()
    if rule_type not in rule_types or rule_types[rule_type] is None:
        return None, False
        
    if rule_type in ['IP-CIDR', 'IP-CIDR6']:
        if len(parts) > 2 and 'no-resolve' in parts[2].lower():
            return f"{rule_type},{parts[1]},no-resolve", True
        return f"{rule_type},{parts[1]}", True
        
    return f"{rule_types[rule_type]},{parts[1]}", True

def process_file(input_path, output_path):
    print(f"Processing {input_path} -> {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(input_path, 'r', encoding='utf-8') as infile:
        rules = []
        skipped_rules = []
        for line in infile:
            converted_rule, is_compatible = convert_rule(line.strip())
            if converted_rule is not None:
                if is_compatible:
                    rules.append(converted_rule)
                else:
                    skipped_rules.append(line.strip())
                    
    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write("# 由Surge规则转换而来\n")
        outfile.write(f"# 原始文件: {input_path}\n")
        if skipped_rules:
            outfile.write("\n# 以下规则在转换时被跳过（不兼容）:\n")
            for rule in skipped_rules:
                outfile.write(f"# {rule}\n")
        outfile.write("\n")
        outfile.write("\n".join(rules))

def main():
    print("Starting conversion...")
    print("Current directory:", os.getcwd())
    print("Directory contents:", os.listdir())
    
    surge_path = Path('rules')
    clash_path = Path('clash-auto/rules')
    
    if not surge_path.exists():
        print(f"Error: {surge_path} does not exist!")
        return
        
    print(f"Found rules directory: {surge_path}")
    print("Rules directory contents:", list(surge_path.glob('**/*.list')))
        
    for file in surge_path.rglob('*.list'):
        relative_path = file.relative_to(surge_path)
        output_file = clash_path / relative_path
        process_file(str(file), str(output_file))

if __name__ == '__main__':
    main()
EOF

      - name: List directory contents
        run: |
          echo "Current directory:"
          pwd
          echo "\nAll contents:"
          ls -R
          echo "\nScript contents:"
          cat scripts/convert-rules.py

      - name: Checkout Clash repository
        uses: actions/checkout@v3
        with:
          repository: USNOCTURNE90/Clash-auto
          token: ${{ secrets.PAT }}
          path: clash-auto

      - name: Convert Rules
        run: |
          ls -la scripts/
          cd scripts
          python convert-rules.py

      - name: List converted files
        run: |
          echo "Checking clash-auto/rules directory:"
          ls -la clash-auto/rules || echo "Rules directory not found"

      - name: Commit and push changes
        if: success()
        run: |
          cd clash-auto
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add rules/
          git commit -m "chore: sync rules from surge repository" || echo "No changes to commit"
          git push origin main
