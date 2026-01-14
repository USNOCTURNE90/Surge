#!/usr/bin/env python3
import os, re, subprocess, ipaddress, logging, traceback
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
def get_china_time():
    return (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

def process_rule_line(line, is_surge=True):
    line = line.strip()
    if not line or line.startswith("#"): return line
    known_prefixes = ["DOMAIN-SUFFIX,", "DOMAIN-KEYWORD,", "DOMAIN,", "IP-CIDR,", "IP-ASN,", "PROCESS-NAME,"]
    if any(line.startswith(prefix) for prefix in known_prefixes): return line
    if "." in line:
        try:
            parts = line.split('.')
            if all(part.isdigit() for part in parts):
                ipaddress.ip_address(line)
                return f"IP-CIDR,{line}/32"
            return f"DOMAIN-SUFFIX,{line}"
        except: return f"DOMAIN-SUFFIX,{line}"
    return f"PROCESS-NAME,{line}"

try:
    root_dir = Path(".")
    rule_files = [f for f in root_dir.glob('*') if f.is_file() and not f.name.startswith('.') and f.suffix not in ['.py', '.yml', '.yaml', '.md']]
    for rule_file in rule_files:
        with open(rule_file, "r", encoding="utf-8") as f:
            content = f.read()
        current_time = get_china_time()
        updated_lines = [f"# 最后更新时间: {current_time} (北京时间)"]
        for line in content.splitlines():
            if not line.startswith("# 最后更新时间:"):
                updated_lines.append(process_rule_line(line))
        updated_content = "\n".join(updated_lines)
        if content != updated_content:
            with open(rule_file, "w", encoding="utf-8") as f:
                f.write(updated_content)
    
    subprocess.run(["git", "add", "."], check=True)
    if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
        subprocess.run(["git", "commit", "-m", f"[AUTO_FORMAT] {get_china_time()}"], check=True)
        subprocess.run(["git", "push"], check=True)
except Exception as e:
    traceback.print_exc()
    exit(1)
