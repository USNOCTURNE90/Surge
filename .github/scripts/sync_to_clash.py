import ipaddress
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

RULE_PREFIXES = (
    'DOMAIN,',
    'DOMAIN-SUFFIX,',
    'DOMAIN-KEYWORD,',
    'IP-CIDR,',
    'IP-CIDR6,',
    'IP-ASN,',
    'PROCESS-NAME,',
)

EXCLUDED_SUFFIXES = {'.py', '.yml', '.yaml', '.json', '.md'}
STATE_DIR = Path('.github/sync_state')
PENDING_FILE = STATE_DIR / 'pending_deletions.json'

def bj_tz():
    return timezone(timedelta(hours=8))

def now_dt():
    return datetime.now(bj_tz())

def now_str():
    return now_dt().strftime('%Y-%m-%d %H:%M:%S (北京时间)')

def now_iso():
    return now_dt().isoformat()

def run(cmd, cwd=None):
    subprocess.run(cmd, check=True, cwd=cwd)

def should_ignore_header(line: str) -> bool:
    prefixes = (
        '# 最后更新时间:',
        '# 从Surge自动同步',
        '# 从Surge自动标准化',
        '# 从Clash自动同步',
        '# 从Clash自动标准化',
        '# 原始文件:',
    )
    return line.startswith(prefixes)

def normalize(line: str):
    line = line.strip()
    if not line:
        return None
    if line.startswith('#'):
        return None
    if line in {'rules:', 'payload:'}:
        return None
    if line.startswith('- '):
        line = line[2:].strip()
    if ' #' in line:
        line = line.split(' #', 1)[0].strip()
    if not line:
        return None
    if line.startswith(RULE_PREFIXES):
        return line

    m = re.fullmatch(r'([^,/]+)(?:/(
    def bj_tz():
    return timezone(timedelta(hours=8))

def now_dt():
    return datetime.now(bj_tz())

def now_str():
    return now_dt().strftime('%Y-%m-%d %H:%M:%S (北京时间)')

def now_iso():
    return now_dt().isoformat()

def run(cmd, cwd=None):
    subprocess.run(cmd, check=True, cwd=cwd)

def should_ignore_header(line: str) -> bool:
    prefixes = (
        '# 最后更新时间:',
        '# 从Surge自动同步',
        '# 从Surge自动标准化',
        '# 从Clash自动同步',
        '# 从Clash自动标准化',
        '# 原始文件:',
    )
    return line.startswith(prefixes)

def normalize(line: str):
    line = line.strip()
    if not line:
        return None
    if line.startswith('#'):
        return None
    if line in {'rules:', 'payload:'}:
        return None
    if line.startswith('- '):
        line = line[2:].strip()
    if ' #' in line:
        line = line.split(' #', 1)[0].strip()
    if not line:
        return None
    if line.startswith(RULE_PREFIXES):
        return line

    m = re.fullmatch(r'([^,/]+)(?:/(
    def bj_tz():
    return timezone(timedelta(hours=8))

def now_dt():
    return datetime.now(bj_tz())

def now_str():
    return now_dt().strftime('%Y-%m-%d %H:%M:%S (北京时间)')

def now_iso():
    return now_dt().isoformat()

def run(cmd, cwd=None):
    subprocess.run(cmd, check=True, cwd=cwd)

def should_ignore_header(line: str) -> bool:
    prefixes = (
        '# 最后更新时间:',
        '# 从Surge自动同步',
        '# 从Surge自动标准化',
        '# 从Clash自动同步',
        '# 从Clash自动标准化',
        '# 原始文件:',
    )
    return line.startswith(prefixes)

def normalize(line: str):
    line = line.strip()
    if not line:
        return None
    if line.startswith('#'):
        return None
    if line in {'rules:', 'payload:'}:
        return None
    if line.startswith('- '):
        line = line[2:].strip()
    if ' #' in line:
        line = line.split(' #', 1)[0].strip()
    if not line:
        return None
    if line.startswith(RULE_PREFIXES):
        return line

    m = re.fullmatch(r'([^,/]+)(?:/(
    def bj_tz():
    return timezone(timedelta(hours=8))

def now_dt():
    return datetime.now(bj_tz())

def now_str():
    return now_dt().strftime('%Y-%m-%d %H:%M:%S (北京时间)')

def now_iso():
    return now_dt().isoformat()

def run(cmd, cwd=None):
    subprocess.run(cmd, check=True, cwd=cwd)

def should_ignore_header(line: str) -> bool:
    prefixes = (
        '# 最后更新时间:',
        '# 从Surge自动同步',
        '# 从Surge自动标准化',
        '# 从Clash自动同步',
        '# 从Clash自动标准化',
        '# 原始文件:',
    )
    return line.startswith(prefixes)

def normalize(line: str):
    line = line.strip()
    if not line:
        return None
    if line.startswith('#'):
        return None
    if line in {'rules:', 'payload:'}:
        return None
    if line.startswith('- '):
        line = line[2:].strip()
    if ' #' in line:
        line = line.split(' #', 1)[0].strip()
    if not line:
        return None
    if line.startswith(RULE_PREFIXES):
        return line

    m = re.fullmatch(r'([^,/]+)(?:/(
    def bj_tz():
    return timezone(timedelta(hours=8))

def now_dt():
    return datetime.now(bj_tz())

def now_str():
    return now_dt().strftime('%Y-%m-%d %H:%M:%S (北京时间)')

