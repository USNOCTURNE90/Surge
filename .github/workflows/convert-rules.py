name: Convert Surge Rules to Clash

on:
  workflow_dispatch:
  push:
    paths:
      - 'rules/**/*'  # 匹配所有规则文件，不限制后缀

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

      - name: Checkout Clash repository
        uses: actions/checkout@v3
        with:
          repository: USNOCTURNE90/Clash-auto
          token: ${{ secrets.PAT }}
          path: clash-auto

      - name: Create converter script
        run: |
          cat > convert.py << 'EOF'
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
                    
    # 添加 .list 后缀到输出文件
    if not output_path.endswith('.list'):
        output_path += '.list'
                    
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
    
    # 检查 rules 目录是否存在
    if not os.path.exists('rules'):
        print("Error: rules directory not found!")
        print("Current directory contents:", os.listdir())
        return
    
    # 处理所有规则文件
    for root, dirs, files in os.walk('rules'):
        for file in files:
            # 忽略隐藏文件和目录
            if not file.startswith('.'):
                input_path = os.path.join(root, file)
                relative_path = os.path.relpath(input_path, 'rules')
                output_path = os.path.join('clash-auto/rules', relative_path)
                process_file(input_path, output_path)

if __name__ == '__main__':
    main()
EOF

      - name: List directories
        run: |
          echo "Current directory contents:"
          ls -la
          echo "\nRules directory contents:"
          ls -R rules || echo "No rules directory found"

      - name: Convert Rules
        run: python convert.py

      - name: Commit and push changes
        run: |
          cd clash-auto
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add rules/
          git commit -m "chore: sync rules from surge repository" || echo "No changes to commit"
          git push origin main
