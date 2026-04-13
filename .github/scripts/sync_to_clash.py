import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

RULE_PREFIXES = (
    "DOMAIN,",
    "DOMAIN-SUFFIX,",
    "DOMAIN-KEYWORD,",
    "IP-CIDR,",
    "IP-CIDR6,",
    "IP-ASN,",
    "PROCESS-NAME,",
)

SKIP_NAMES = {"README.md"}
SKIP_DIRS = {".git", ".github"}
STATE_PATH = Path(".github/sync_state/deletions_to_clash.json")
GRACE_SECONDS = 300


def bj_tz():
    return timezone(timedelta(hours=8))


def bj_now():
    return datetime.now(bj_tz()).strftime("%Y-%m-%d %H:%M:%S (北京时间)")


def bj_now_iso():
    return datetime.now(bj_tz()).isoformat()


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def normalize(line: str):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith(RULE_PREFIXES):
        return line
    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", line):
        return f"IP-CIDR,{line}/32"
    if "." in line:
        return f"DOMAIN-SUFFIX,{line}"
    return line


def is_rule_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name in SKIP_NAMES:
        return False
    if path.name.startswith("."):
        return False
    if path.suffix in {".py", ".yml", ".yaml", ".md", ".json"}:
        return False
    return True


def load_state():
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


state = load_state()

repo = Path("clash_repo")
if repo.exists():
    shutil.rmtree(repo)

subprocess.run(
    [
        "git",
        "clone",
        f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/{os.environ['TARGET_REPO']}.git",
        "clash_repo",
    ],
    check=True,
)
subprocess.run(
    ["git", "-C", "clash_repo", "checkout", os.environ["TARGET_BRANCH"]],
    check=True,
)

source_files = {
    p.name: p
    for p in Path(".").iterdir()
    if p.name not in SKIP_DIRS and is_rule_file(p)
}
target_files = {
    p.name: p
    for p in repo.iterdir()
    if p.is_file() and not p.name.startswith(".") and p.suffix not in {".py", ".yml", ".yaml", ".md", ".json"}
}

changed = False
now = datetime.now(bj_tz())

# 正常同步存在的文件
for name, p in source_files.items():
    lines = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        n = normalize(raw)
        if n:
            lines.append(n)

    out = (
        f"# 最后更新时间: {bj_now()}\n"
        "# 从Surge自动同步\n"
        f"# 原始文件: {p.name}\n"
        "rules:\n"
        + "\n".join(f"  - {x}" for x in lines)
        + "\n"
    )

    target = repo / p.name
    old = target.read_text(encoding="utf-8") if target.exists() else None
    if old != out:
        target.write_text(out, encoding="utf-8")
        changed = True

    if name in state:
        del state[name]

# 删除冷静期：发现另一边有、这边没有的文件时，5 分钟内不恢复也不删除
for name in target_files:
    if name in source_files:
        continue

    stamp = state.get(name)
    if not stamp:
        state[name] = bj_now_iso()
        continue

    if (now - parse_iso(stamp)).total_seconds() < GRACE_SECONDS:
        continue

    # 超过 5 分钟后，仍然不自动恢复，让你手动决定
    # 只保留删除标记，避免文件自动回来
    continue

save_state(state)

if changed:
    subprocess.run(
        ["git", "-C", "clash_repo", "config", "user.name", "github-actions[bot]"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            "clash_repo",
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
        ],
        check=True,
    )
    subprocess.run(["git", "-C", "clash_repo", "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            "clash_repo",
            "commit",
            "-m",
            f"[AUTO_SYNC] 从Surge自动同步规则集 - {bj_now()}",
        ],
        check=True,
    )
    subprocess.run(["git", "-C", "clash_repo", "push"], check=True)

# 提交本仓库的删除状态文件
subprocess.run(["git", "add", str(STATE_PATH)], check=False)
status = subprocess.run(
    ["git", "status", "--porcelain", "--", str(STATE_PATH)],
    capture_output=True,
    text=True,
    check=True,
)
if status.stdout.strip():
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        [
            "git",
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
        ],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            f"[AUTO_SYNC] 更新删除冷静期状态 - {bj_now()}",
        ],
        check=True,
    )
    subprocess.run(["git", "push"], check=True)