import os

def convert_rule(line):
    # 保持注释行的原有格式，但确保#前没有空格
    if line.lstrip().startswith('#'):
        return line.lstrip()
    return line

def process_file(surge_path, clash_path):
    os.makedirs(os.path.dirname(clash_path), exist_ok=True)
    
    with open(surge_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    converted_lines = []
    for line in lines:
        if line.strip():
            converted_line = convert_rule(line.rstrip('\n'))
            converted_lines.append(converted_line)
        else:
            converted_lines.append(line.rstrip('\n'))
    
    with open(clash_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(converted_lines))

def main():
    surge_dir = 'surge'
    clash_dir = 'clash'
    
    for root, _, files in os.walk(surge_dir):
        for file in files:
            surge_path = os.path.join(root, file)
            relative_path = os.path.relpath(surge_path, surge_dir)
            clash_path = os.path.join(clash_dir, relative_path)
            process_file(surge_path, clash_path)

if __name__ == '__main__':
    main()
