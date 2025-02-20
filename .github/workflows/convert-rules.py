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
    print(f"开始处理文件: {input_path} -> {output_path}")
    
    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        print(f"错误: 输入文件不存在: {input_path}")
        return False
        
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
        
        print(f"转换完成: 成功转换 {len(rules)} 条规则，跳过 {len(skipped_rules)} 条规则")
                    
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
            
        print(f"文件已保存: {output_path}")
        return True
        
    except Exception as e:
        print(f"处理文件时出错: {e}")
        return False

def main():
    print("=== 开始规则转换 ===")
    print("当前工作目录:", os.getcwd())
    print("目录内容:", os.listdir())
    
    # 检查 rules 目录
    if not os.path.exists('rules'):
        print("错误: rules 目录不存在!")
        print("当前目录内容:", os.listdir())
        return
    
    print("Found rules directory:", os.listdir('rules'))
    
    # 检查 clash-auto 目录
    if not os.path.exists('clash-auto'):
        print("错误: clash-auto 目录不存在!")
        return
        
    print("Found clash-auto directory:", os.listdir('clash-auto'))
    
    # 处理所有规则文件
    processed_files = 0
    for root, dirs, files in os.walk('rules'):
        for file in files:
            if not file.startswith('.'):
                input_path = os.path.join(root, file)
                # 保持目录结构
                rel_path = os.path.relpath(input_path, 'rules')
                output_path = os.path.join('clash-auto', rel_path)
                
                if process_file(input_path, output_path):
                    processed_files += 1
    
    print(f"=== 转换完成 ===")
    print(f"共处理 {processed_files} 个文件")

if __name__ == '__main__':
    main()
