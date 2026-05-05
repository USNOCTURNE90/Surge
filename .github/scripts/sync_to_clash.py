import ipaddress
import json
import os
import re
import subprocess
import tempfile
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
PENDING_MARKER = '# ⏳ 此文件已在 Surge 中删除，将于'

CN_PUNCT = str.maketrans('，。、；：', ',.,;:')

def bj_tz():
    return timezone(timedelta(hours=8))

def now_dt():
    return datetime.now(bj_tz())

def now_str():
    return now_dt().strftime('%Y-%m-%d %H:%M:%S (北京时间)')

def now_iso():
    return now_dt().isoformat()

def delete_at_str(requested_iso: str) -> str:
    dt = datetime.fromisoformat(requested_iso) + timedelta(minutes=5)
    return dt.strftime('%Y-%m-%d %H:%M:%S (北京时间)')

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
        PENDING_MARKER,
    )
    return line.startswith(prefixes)

def has_chinese(s: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', s))

def normalize(line: str):
    line = line.strip()
    if not line.startswith('#'):
        line = line.translate(CN_PUNCT)
    if not line:
        return None
    # 注释行原样保留
    if line.startswith('#'):
        return line
    if line in {'rules:', 'payload:'}:
        return None
    if line.startswith('- '):
        line = line[2:].strip()
    if ' #' in line:
        line = line.split(' #', 1)[0].strip()
    if not line:
        return None
    # 已有合法前缀，原样保留
    if line.startswith(RULE_PREFIXES):
        return line
    # 含中文且无合法前缀，原样保留，不加前缀
    if has_chinese(line):
        return line

    m = re.fullmatch(r'([^,/]+)(?:/([0-9]{1,2}))?(?:,(no-resolve))?', line, re.IGNORECASE)
    if m:
        raw_ip = m.group(1)
        mask = m.group(2)
        extra = f',{m.group(3)}' if m.group(3) else ''
        try:
            ipaddress.IPv4Address(raw_ip)
            return f'IP-CIDR,{raw_ip}/{mask or "32"}{extra}'
        except ValueError:
            pass

    if '.' in line:
        return f'DOMAIN-SUFFIX,{line}'

    return f'PROCESS-NAME,{line}'

def parse_rules_from_file(path: Path):
    rules = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith('#'):
            if should_ignore_header(raw):
                continue
            # 非系统头注释，原样保留
            rules.append(raw)
            continue
        n = normalize(raw)
        if n:
            rules.append(n)
    return rules

def ensure_state():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not PENDING_FILE.exists():
        PENDING_FILE.write_text('[]\n', encoding='utf-8')

def load_pending():
    ensure_state()
    try:
        return json.loads(PENDING_FILE.read_text(encoding='utf-8'))
    except Exception:
        return []

def save_pending(items):
    ensure_state()
    PENDING_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def fix_current_repo_remote():
    token = os.environ['GITHUB_TOKEN']
    run(['git', 'remote', 'set-url', 'origin', f'https://x-access-token:{token}@github.com/USNOCTURNE90/Surge.git'])

target_checkout = tempfile.TemporaryDirectory(prefix='clash_repo_')
repo = Path(target_checkout.name) / 'repo'

run(['git', 'clone', f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/{os.environ['TARGET_REPO']}.git", str(repo)])
run(['git', '-C', str(repo), 'checkout', os.environ['TARGET_BRANCH']])

ensure_state()
pending = load_pending()

# 只对已确认写入标记的条目，检查用户是否删除了标记行
cancelled = set()
for item in list(pending):
    if item.get('repo') != 'Surge' or item.get('target_repo') != 'Clash':
        continue
    if not item.get('marker_written'):
        continue
    filename = item['filename']
    target = repo / filename
    if target.exists():
        content = target.read_text(encoding='utf-8')
        if not content.startswith(PENDING_MARKER):
            cancelled.add(filename)

pending = [x for x in pending if not (
    x.get('repo') == 'Surge' and
    x.get('target_repo') == 'Clash' and
    x.get('filename') in cancelled
)]

changed_local = False
changed_remote = False
source_names = set()

for p in Path('.').iterdir():
    if not p.is_file() or p.name.startswith('.') or p.suffix in EXCLUDED_SUFFIXES:
        continue

    source_names.add(p.name)
    rules = parse_rules_from_file(p)

    local_output = (
        f'# 最后更新时间: {now_str()}\n'
        '# 从Surge自动标准化\n'
        f'# 原始文件: {p.name}\n'
        + '\n'.join(rules)
        + '\n'
    )

    old_local = p.read_text(encoding='utf-8')
    if old_local != local_output:
        p.write_text(local_output, encoding='utf-8')
        changed_local = True

    in_pending = any(
        x.get('repo') == 'Surge' and
        x.get('target_repo') == 'Clash' and
        x.get('filename') == p.name
        for x in pending
    )
    if in_pending:
        continue

    remote_output = (
        f'# 最后更新时间: {now_str()}\n'
        '# 从Surge自动同步\n'
        f'# 原始文件: {p.name}\n'
        'rules:\n'
        + '\n'.join(f'  - {rule}' for rule in rules)
        + '\n'
    )

    target = repo / p.name
    old_remote = target.read_text(encoding='utf-8') if target.exists() else None
    if old_remote != remote_output:
        target.write_text(remote_output, encoding='utf-8')
        changed_remote = True

target_existing = set()
for rp in repo.iterdir():
    if rp.is_file() and not rp.name.startswith('.') and rp.suffix not in EXCLUDED_SUFFIXES:
        target_existing.add(rp.name)

for name in sorted(target_existing - source_names):
    already = any(
        x.get('repo') == 'Surge' and
        x.get('target_repo') == 'Clash' and
        x.get('filename') == name
        for x in pending
    )
    if not already:
        requested_iso = now_iso()
        target = repo / name
        marker_written = False
        if target.exists():
            old_content = target.read_text(encoding='utf-8')
            marker_line = f'{PENDING_MARKER} {delete_at_str(requested_iso)} 自动删除 — 删除本行立即取消删除并恢复文件\n'
            if not old_content.startswith(PENDING_MARKER):
                target.write_text(marker_line + old_content, encoding='utf-8')
                changed_remote = True
                marker_written = True
        pending.append({
            'repo': 'Surge',
            'target_repo': 'Clash',
            'filename': name,
            'requested_at': requested_iso,
            'marker_written': marker_written,
        })
        changed_local = True
    else:
        for item in pending:
            if (item.get('repo') == 'Surge' and
                item.get('target_repo') == 'Clash' and
                item.get('filename') == name and
                not item.get('marker_written')):
                target = repo / name
                if target.exists():
                    old_content = target.read_text(encoding='utf-8')
                    marker_line = f'{PENDING_MARKER} {delete_at_str(item["requested_at"])} 自动删除 — 删除本行立即取消删除并恢复文件\n'
                    if not old_content.startswith(PENDING_MARKER):
                        target.write_text(marker_line + old_content, encoding='utf-8')
                        changed_remote = True
                        item['marker_written'] = True
                        changed_local = True

save_pending(pending)

if changed_local:
    run(['git', 'config', 'user.name', 'github-actions[bot]'])
    run(['git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'])
    fix_current_repo_remote()
    run(['git', 'add', '.'])
    status = subprocess.run(['git', 'diff', '--cached', '--quiet'])
    if status.returncode != 0:
        run(['git', 'commit', '-m', f'[AUTO_SYNC] 本地格式化 Surge 规则集 - {now_str()}'])
        run(['git', 'push'])

if changed_remote:
    run(['git', '-C', str(repo), 'config', 'user.name', 'github-actions[bot]'])
    run(['git', '-C', str(repo), 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'])
    run(['git', '-C', str(repo), 'remote', 'set-url', 'origin', f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/{os.environ['TARGET_REPO']}.git"])
    run(['git', '-C', str(repo), 'add', '.'])
    status = subprocess.run(['git', '-C', str(repo), 'diff', '--cached', '--quiet'])
    if status.returncode != 0:
        run(['git', '-C', str(repo), 'commit', '-m', f'[AUTO_SYNC] 从Surge自动同步规则集 - {now_str()}'])
        run(['git', '-C', str(repo), 'push'])
