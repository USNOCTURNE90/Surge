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
    """从文件内容中获取规则集名称"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('#'):
                # 移除 # 和空格
                return first_line.lstrip('#').strip()
    except:
        pass
    # 如果没有找到名称，使用文件名
    return os.path.basename(file_path)

def process_file(input_path, output_path):
    ruleset_name = get_ruleset_name(input_path)
    print(f"\n=== 正在处理规则集: {ruleset_name} ===")
    print(f"输入文件: {input_path}")
    print(f"输出文件: {output_path}")
    
    try:
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
                    
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write("# 由Surge规则转换而来\n")
            outfile.write(f"# 规则集: {ruleset_name}\n")
            outfile.write(f"# 原始文件: {input_path}\n")
            if skipped_rules:
                outfile.write("\n# 以下规则在转换时被跳过（不兼容）:\n")
                for rule in skipped_rules:
                    outfile.write(f"# {rule}\n")
            outfile.write("\n")
            outfile.write("\n".join(rules))
            
        print(f"规则集 {ruleset_name} 处理完成")
        print(f"- 转换规则数: {len(rules)}")
        print(f"- 跳过规则数: {len(skipped_rules)}")
        return True
    except Exception as e:
        print(f"处理规则集 {ruleset_name} 时出错: {str(e)}")
        return False

def main():
    print("\n=== 开始转换规则 ===")
    print(f"当前工作目录: {os.getcwd()}")
    
    processed_count = 0
    
    # 遍历所有目录
    for item in os.listdir():
        if item.startswith('.') or item == 'clash-auto':
            continue
            
        item_path = os.path.join(os.getcwd(), item)
        if os.path.isdir(item_path):
            # 遍历目录中的所有文件
            for root, dirs, files in os.walk(item_path):
                for file in files:
                    if not file.startswith('.'):
                        input_path = os.path.join(root, file)
                        rel_path = os.path.relpath(input_path, os.getcwd())
                        output_path = os.path.join('clash-auto', rel_path)
                        
                        if process_file(input_path, output_path):
                            processed_count += 1
    
    print(f"\n=== 转换完成 ===")
    print(f"总共处理规则集数量: {processed_count}")

if __name__ == '__main__':
    main()
