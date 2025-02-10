import os
import sys

def process_files(surge_path, clash_path=None, output_path='output.yaml'):
    try:
        with open(surge_path, 'r', encoding='utf-8') as f:
            original_lines = f.readlines()
    except FileNotFoundError:
        print(f"错误: 找不到 Surge 规则文件: {surge_path}")
        return
        
    processed_rules = set()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # 写入 rules 开头
        f.write('rules:\n')
        
        for line in original_lines:
            stripped_line = line.strip()
            
            if stripped_line.startswith('#'):
                indent = len(line) - len(line.lstrip())
                content = line.lstrip()[1:]
                f.write(' ' * indent + '#' + content)
                continue
            
            if stripped_line:
                parts = stripped_line.split(',')
                if len(parts) >= 2:
                    rule_type = parts[0].strip().upper()
                    if rule_type == 'PROCESS-NAME':
                        rule = f'  - PROCESS-NAME,{parts[1].strip()}'
                        if rule not in processed_rules:
                            processed_rules.add(rule)
                            f.write(rule + '\n')
                        continue
                    elif rule_type in ['DOMAIN-SUFFIX', 'DOMAIN', 'DOMAIN-KEYWORD', 'IP-CIDR', 'IP-CIDR6', 'USER-AGENT']:
                        if rule_type in ['IP-CIDR', 'IP-CIDR6'] and len(parts) > 2 and 'no-resolve' in parts[2]:
                            rule = f'  - {rule_type},{parts[1].strip()},no-resolve'
                        else:
                            rule = f'  - {rule_type},{parts[1].strip()}'
                            
                        if rule not in processed_rules:
                            processed_rules.add(rule)
                            f.write(rule + '\n')
                        continue
            
            if not any(stripped_line.startswith(prefix) for prefix in ['DOMAIN-SUFFIX,', 'DOMAIN,', 'DOMAIN-KEYWORD,', 'IP-CIDR,', 'IP-CIDR6,', 'USER-AGENT,', 'PROCESS-NAME,']):
                f.write(line)

    if clash_path:
        try:
            new_rules = []
            with open(clash_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped_line = line.strip()
                    if stripped_line.startswith('  - ') and stripped_line not in processed_rules:
                        new_rules.append(stripped_line)
            
            if new_rules:
                with open(output_path, 'a', encoding='utf-8') as f:
                    for rule in new_rules:
                        f.write(rule + '\n')
                        processed_rules.add(rule)
        except FileNotFoundError:
            print(f"警告: 找不到 Clash 规则文件: {clash_path}")

    print(f"转换完成！")
    print(f"规则总数: {len(processed_rules)}")

def main():
    surge_dir = 'surge'
    clash_dir = 'clash'
    
    for root, _, files in os.walk(surge_dir):
        for file in files:
            surge_path = os.path.join(root, file)
            relative_path = os.path.relpath(surge_path, surge_dir)
            clash_path = os.path.join(clash_dir, relative_path)
            process_files(surge_path, None, clash_path)

if __name__ == '__main__':
    main()
