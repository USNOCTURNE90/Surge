import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_DIR = Path('.github/sync_state')
PENDING_FILE = STATE_DIR / 'pending_deletions.json'
PENDING_MARKER = '# ⏳ 此文件已在 Surge 中删除，将于'

def bj_tz():
    return timezone(timedelta(hours=8))

def now_dt():
    return datetime.now(bj_tz())

def now_str():
    return now_dt().strftime('%Y-%m-%d %H:%M:%S (北京时间)')

def run(cmd, cwd=None):
    subprocess.run(cmd, check=True, cwd=cwd)

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

target_checkout = tempfile.TemporaryDirectory(prefix='clash_repo_')
repo = Path(target_checkout.name) / 'repo'

run([
    'git', 'clone',
    f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/{os.environ['TARGET_REPO']}.git",
    str(repo)
])
run(['git', '-C', str(repo), 'checkout', os.environ['TARGET_BRANCH']])

pending = load_pending()
remaining = []
changed_remote = False
changed_local = False

for item in pending:
    if item.get('repo') != 'Surge' or item.get('target_repo') != 'Clash':
        remaining.append(item)
        continue

    requested_at = datetime.fromisoformat(item['requested_at'])
    if now_dt() - requested_at < timedelta(minutes=5):
        remaining.append(item)
        continue

    filename = item['filename']
    target = repo / filename
    if not target.exists():
        continue

    # 确认文件顶部还有待删除标记才删除（防止用户已取消）
    content = target.read_text(encoding='utf-8')
    if not content.startswith(PENDING_MARKER):
        remaining.append(item)
        continue

    target.unlink()
    changed_remote = True

if changed_remote:
    run(['git', '-C', str(repo), 'config', 'user.name', 'github-actions[bot]'])
    run(['git', '-C', str(repo), 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'])
    run(['git', '-C', str(repo), 'remote', 'set-url', 'origin', f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/{os.environ['TARGET_REPO']}.git"])
    run(['git', '-C', str(repo), 'add', '.'])
    status = subprocess.run(['git', '-C', str(repo), 'diff', '--cached', '--quiet'])
    if status.returncode != 0:
        run(['git', '-C', str(repo), 'commit', '-m', f"[AUTO_SYNC] 处理来自Surge的延迟删除 - {now_str()}"])
        run(['git', '-C', str(repo), 'push'])

if pending != remaining:
    save_pending(remaining)
    changed_local = True

if changed_local:
    run(['git', 'config', 'user.name', 'github-actions[bot]'])
    run(['git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'])
    run(['git', 'remote', 'set-url', 'origin', f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/USNOCTURNE90/Surge.git"])
    run(['git', 'add', '.'])
    status = subprocess.run(['git', 'diff', '--cached', '--quiet'])
    if status.returncode != 0:
        run(['git', 'commit', '-m', f"[AUTO_SYNC] 更新Surge待删除状态 - {now_str()}"])
        run(['git', 'push'])
