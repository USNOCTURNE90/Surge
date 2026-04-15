import re

# Existing code...


def normalize(line):
    # Previous lines...
    if line.startswith('#'):
        return line

    # Existing code...
    if re.search(r'[\u4e00-\u9fff]', line):
        return line

    if '.' in line:
        return f'DOMAIN-SUFFIX,{line}'

    return f'PROCESS-NAME,{line}'


def parse_rules_from_file(file_path):
    # Previous code...
    for raw in lines:
        if raw.startswith('#'):
            if should_ignore_header(raw):
                continue
            n = normalize(raw)
            if n:
                rules.append(n)
            continue
    # Existing code...
