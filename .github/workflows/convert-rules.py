name: Convert Surge Rules to Clash

on:
  workflow_dispatch:

jobs:
  convert:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout Surge repository
        uses: actions/checkout@v3

      - name: Debug Info
        run: |
          echo "Current directory contents:"
          pwd
          ls -la
          echo "\nWorkflows directory contents:"
          ls -la .github/workflows/ || echo "Workflows directory not found"

      - name: Create converter script
        run: |
          mkdir -p .github/workflows
          cat > .github/workflows/convert-rules.py << 'EOF'
import os
import re
from pathlib import Path

def convert_rule(line):
    """转换单条规则，返回转换后的规则和是否兼容的标志"""
    # 跳过注释和空行
    if line.startswith('#') or not line.strip():
        return line, True

    # 常见的规则类型转换映射
    rule_types = {
        'DOMAIN-SUFFIX': 'DOMAIN-SUFFIX',
        'DOMAIN': 'DOMAIN',
        'DOMAIN-KEYWORD': 'DOMAIN-KEYWORD',
        'IP-CIDR': 'IP-CIDR',
        'IP-CIDR6': 'IP-CIDR6',
        'PROCESS-NAME': None,  # Clash不支持
        'USER-AGENT': None,  # Clash不支持
    }

    # 解析规则
    parts = line.strip().split(',')
    if len(parts) < 2:
        return None, False

    rule_type = parts[0].upper()
    
    # 检查规则类型是否支持
    if rule_type not in rule_types or rule_types[rule_type] is None:
        return None, False

    # 特殊处理IP-CIDR规则
    if rule_type in ['IP-CIDR', 'IP-CIDR6']:
        if len(parts) > 2 and 'no-resolve' in parts[2].lower():
            return f"{rule_type},{parts[1]},no-resolve", True
        return f"{rule_type},{parts[1]}", True

    # 转换基本规则
    return f"{rule_types[rule_type]},{parts[1]}", True

def process_file(input_path, output_path):
    """处理单个规则文件"""
    print(f"Processing file: {input_path} -> {output_path}")
    
    # 确保输出目录存在
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

    # 写入转换后的规则
    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write("# 由Surge规则转换而来\n")
        outfile.write("# 原始文件: {}\n".format(input_path))
        if skipped_rules:
            outfile.write("\n# 以下规则在转换时被跳过（不兼容）:\n")
            for rule in skipped_rules:
                outfile.write("# {}\n".format(rule))
        outfile.write("\n")
        outfile.write("\n".join(rules))

def main():
    print("Starting conversion process...")
    surge_path = Path(os.environ.get('SURGE_RULES_PATH', 'rules'))
    clash_path = Path(os.environ.get('CLASH_RULES_PATH', 'clash-auto/rules'))
    
    print(f"Source path: {surge_path}")
    print(f"Target path: {clash_path}")

    # 列出当前目录内容
    print("\nCurrent directory contents:")
    os.system('ls -la')
    
    # 检查源目录是否存在
    if not surge_path.exists():
        print(f"Error: Source path {surge_path} does not exist!")
        return

    # 遍历所有规则文件
    for file in surge_path.rglob('*.list'):
        relative_path = file.relative_to(surge_path)
        output_file = clash_path / relative_path
        
        print(f"\nConverting {file} to {output_file}")
        process_file(str(file), str(output_file))

if __name__ == '__main__':
    main()
EOF

      - name: Checkout Clash repository
        uses: actions/checkout@v3
        with:
          repository: USNOCTURNE90/Clash-auto
          token: ${{ secrets.PAT }}
          path: clash-auto

      - name: Convert Rules
        run: |
          python .github/workflows/convert-rules.py
        env:
          SURGE_RULES_PATH: rules
          CLASH_RULES_PATH: clash-auto/rules

      - name: Commit and push changes
        run: |
          cd clash-auto
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add rules/
          git commit -m "chore: sync rules from surge repository" || echo "No changes to commit"
          git push origin main
