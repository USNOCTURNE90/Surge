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
    
    if not os.path.exists('rules'):
        print("Error: rules directory not found!")
        print("Current directory contents:", os.listdir())
        return
    
    for root, dirs, files in os.walk('rules'):
        for file in files:
            if not file.startswith('.'):
                input_path = os.path.join(root, file)
                # 把文件直接输出到 clash-auto 根目录
                output_path = os.path.join('clash-auto', os.path.basename(input_path))
                process_file(input_path, output_path)

if __name__ == '__main__':
    main()
