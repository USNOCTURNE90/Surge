#!/usr/bin/env python3

import ipaddress
import os
import subprocess
import traceback
from datetime import datetime, timedelta
from pathlib import Path

KNOWN_PREFIXES = (
    "DOMAIN-SUFFIX,",
    "DOMAIN-KEYWORD,",
    "DOMAIN,",
    "IP-CIDR,",
    "IP-ASN,",
    "PROCESS-NAME,",
)
TIMESTAMP_PREFIX = "# 最后更新时间:"


def get_china_time():
    utc_now = datetime.utcnow()
    china_time = utc_now + timedelta(hours=8)
    return china_time.strftime("%Y-%m-%d %H:%M:%S")


def normalize_rule_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return line

    if any(line.startswith(prefix) for prefix in KNOWN_PREFIXES):
        return line

    try:
        network = ipaddress.ip_network(line, strict=False)
        if isinstance(network, ipaddress.IPv4Network):
            return f"IP-CIDR,{network.with_prefixlen}"
        return line
    except ValueError:
        pass

    try:
        address = ipaddress.ip_address(line)
        if isinstance(address, ipaddress.IPv4Address):
            return f"IP-CIDR,{address}/32"
        return line
    except ValueError:
        pass

    if "." in line and "," not in line and " " not in line:
        return f"DOMAIN-SUFFIX,{line}"

    if "." not in line and "," not in line and " " not in line:
        return f"PROCESS-NAME,{line}"

    return line


def should_exclude(path):
    if path.is_dir() or path.name.startswith("."):
        return True

    excluded_names = {".gitignore", "LICENSE", "format_rules.py"}
    excluded_suffixes = {".yml", ".yaml", ".py", ".md"}
    if path.name in excluded_names:
        return True
    if path.name.startswith("README"):
        return True
    if path.suffix in excluded_suffixes:
        return True
    return False


def strip_timestamp(lines):
    return [line for line in lines if not line.startswith(TIMESTAMP_PREFIX)]


def build_updated_lines(content):
    current_time = get_china_time()
    content_lines = content.splitlines()
    body_lines = []

    for line in content_lines:
        if line.startswith(TIMESTAMP_PREFIX):
            continue
        body_lines.append(normalize_rule_line(line))

    updated_lines = [f"# 最后更新时间: {current_time} (北京时间)", *body_lines]

    if strip_timestamp(updated_lines) == strip_timestamp(content_lines):
        return None
    return updated_lines


print(f"Current directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")

try:
    root_dir = Path(".")
    rule_files = []

    for file_path in root_dir.glob("*"):
        if should_exclude(file_path):
            print(f"Skipping excluded file: {file_path}")
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
            if any(marker in content for marker in ("DOMAIN", "IP-CIDR", ".")):
                rule_files.append(file_path)
                print(f"Found rule file: {file_path.name}")
        except Exception as exc:
            print(f"Error reading {file_path.name}: {exc}")

    if not rule_files:
        print("No rule files found!")
        print(f"All files: {[f.name for f in root_dir.glob('*') if not should_exclude(f)]}")
        raise SystemExit(1)

    changed_files = []
    for rule_file in rule_files:
        content = rule_file.read_text(encoding="utf-8")
        updated_lines = build_updated_lines(content)
        if updated_lines is None:
            continue

        rule_file.write_text("\n".join(updated_lines), encoding="utf-8")
        changed_files.append(rule_file.name)
        print(f"Updated rule file: {rule_file.name}")

    if not changed_files:
        print("No substantive rule changes detected in current repo")
        raise SystemExit(0)

    subprocess.run(["git", "add", "--", *changed_files], check=True)

    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *changed_files],
        capture_output=True,
        text=True,
        check=True,
    )

    if not result.stdout.strip():
        print("No changes to commit in current repo")
        raise SystemExit(0)

    print("Changes found in current repo, committing...")
    commit_message = f"[AUTO_FORMAT] 自动格式化规则集 - {get_china_time()} (北京时间)"
    subprocess.run(["git", "commit", "-m", commit_message], check=True)

    print("Pushing changes to current repo...")
    subprocess.run(["git", "push"], check=True)
    print("Successfully updated current repo")

except Exception as exc:
    print(f"Error: {exc}")
    traceback.print_exc()
    raise SystemExit(1)
