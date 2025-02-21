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
        'PROCESS-NAME': 'PROCESS-NAME',
        'USER-AGENT': 'USER-AGENT'
    }
    
    parts = line.strip().split(',')
    if len(parts) < 2:
        return None, False
        
    rule_type = parts[0].upper()
    if rule_type not in rule_types:
        return None, False
        
    if rule_type in ['IP-CIDR', 'IP-CIDR6']:
        if len(parts) > 2 and 'no-resolve' in parts[2].lower():
            return f"{rule_type},{parts[1]},no-resolve", True
        return f"{rule_type},{parts[1]}", True
        
    return f"{rule_types[rule_type]},{parts[1]}", True

def get_ruleset_name(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('#'):
                return first_line.lstrip('#').strip()
    except:
        pass
    return os.path.basename(file_path)

def process_file(input_path, output_path):
    ruleset_name = get_ruleset_name(input_path)
    print(f"\n=== Processing ruleset: {ruleset_name} ===")
    print(f"Input file: {input_path}")
    print(f"Output file: {output_path}")
    
    try:
        if not os.path.exists(input_path):
            print(f"Input file not found: {input_path}")
            return False
            
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
                    
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write("# Converted from Surge rules\n")
            outfile.write(f"# Ruleset: {ruleset_name}\n")
            outfile.write(f"# Original file: {input_path}\n")
            if skipped_rules:
                outfile.write("\n# Skipped incompatible rules:\n")
                for rule in skipped_rules:
                    outfile.write(f"# {rule}\n")
            outfile.write("\n")
            outfile.write("\n".join(rules))
            
        print(f"Ruleset {ruleset_name} processed successfully")
        print(f"- Converted rules: {len(rules)}")
        print(f"- Skipped rules: {len(skipped_rules)}")
        return True
    except Exception as e:
        print(f"Error processing ruleset {ruleset_name}: {str(e)}")
        return False

def main():
    print("\n=== Starting rule conversion ===")
    print(f"Current working directory: {os.getcwd()}")
    
    processed_count = 0
    input_dir = os.getenv('INPUT_DIR', '.')  # 可以设置为环境变量
    output_base_dir = os.getenv('OUTPUT_DIR', 'clash-auto')
    
    # 创建输出目录
    os.makedirs(output_base_dir, exist_ok=True)
    
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.startswith('.') or 'clash-auto' in root:
                continue
                
            input_path = os.path.join(root, file)
            rel_path = os.path.relpath(input_path, input_dir)
            output_path = os.path.join(output_base_dir, rel_path)
            
            if process_file(input_path, output_path):
                processed_count += 1
    
    print(f"\n=== Conversion completed ===")
    print(f"Total processed rulesets: {processed_count}")

if __name__ == '__main__':
    main()
