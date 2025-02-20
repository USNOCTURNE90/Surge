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
    print(f"处理文件: {input_path} -> {output_path}")
    
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
                    
        # 添加 .list 后缀到输出文件
        if not output_path.endswith('.list'):
            output_path += '.list'
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write("# 由Surge规则转换而来\n")
            outfile.write(f"# 原始文件: {input_path}\n")
            if skipped_rules:
                outfile.write("\n# 以下规则在转换时被跳过（不兼容）:\n")
                for rule in skipped_rules:
                    outfile.write(f"# {rule}\n")
            outfile.write("\n")
            outfile.write("\n".join(rules))
            print(f"成功写入文件: {output_path}")
        return True
    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        return False

def main():
    print("=== 开始转换规则 ===")
    print("当前目录:", os.getcwd())
    
    # 要处理的目录列表
    directories = [
        'AI', 'AppleDirect', 'AppleProxyRules', 'Crypto',
        'Facebook', 'Financial'
    ]
    
    converted_count = 0
    for directory in directories:
        if os.path.exists(directory):
            print(f"\n处理目录: {directory}")
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if not file.startswith('.'):  # 跳过隐藏文件
                        input_path = os.path.join(root, file)
                        # 保持相同的目录结构
                        rel_path = os.path.relpath(input_path)
                        output_path = os.path.join('clash-auto', rel_path)
                        if process_file(input_path, output_path):
                            converted_count += 1
    
    print(f"\n=== 转换完成 ===")
    print(f"共转换 {converted_count} 个文件")

if __name__ == '__main__':
    main()
