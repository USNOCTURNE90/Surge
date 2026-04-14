import ipaddress
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
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

EXCLUDED_SUFFIXES = {".py", ".yml", ".yaml", ".json", ".md"}


def bj_tz():
    return timezone(timedelta(hours=8))


def now_str():
    return datetime.now(bj_tz()).strftime("%Y-%m-%d %H:%M:%S (北京时间)")


def should_ignore_header(line: str) -> bool:
    prefixes = (
        "# 最后更新时间:",
        "# 从Surge自动同步",
        "# 从Surge自动标准化",
        "# 从Clash自动同步",
        "# 从Clash自动标准化",
        "# 原始文件:",
    )
    return line.startswith(prefixes)


def normalize(line: str):
    line = line.strip()

    if not line:
        return None

    if line.startswith("#"):
        return None

    if line in {"rules:", "payload:"}:
        return None

    if line.startswith("- "):
        line = line[2:].strip()

    if " #" in line:
        line = line.split(" #", 1)[0].strip()

    if not line:
        return None

    if line.startswith(RULE_PREFIXES):
        return line

    m = re.fullmatch(
        r"([^,/]+)(?:/(\d{1,2}))?(?:,(no-resolve))?",
        line,
        re.IGNORECASE,
    )
    if m:
        raw_ip = m.group(1)
        mask = m.group(2)
        extra = f",{m.group(3)}" if m.group(3) else ""
        try:
            ipaddress.IPv4Address(raw_ip)
            return f"IP-CIDR,{raw_ip}/{mask or '32'}{extra}"
        except ValueError:
            pass

    if "." in line:
        return f"DOMAIN-SUFFIX,{line}"

    return line


def parse_rules_from_file(path: Path):
    rules = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith("#"):
            if should_ignore_header(raw):
                continue
            continue
        n = normalize(raw)
        if n:
            rules.append(n)
    return rules


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

changed_local = False
changed_remote = False

for p in Path(".").iterdir():
    if (
        not p.is_file()
        or p.name.startswith(".")
        or p.suffix in EXCLUDED_SUFFIXES
    ):
        continue

    rules = parse_rules_from_file(p)

    # Surge 本地标准化为纯文本规则
    local_output = (
        f"# 最后更新时间: {now_str()}\n"
        "# 从Surge自动标准化\n"
        f"# 原始文件: {p.name}\n"
        + "\n".join(rules)
        + "\n"
    )

    old_local = p.read_text(encoding="utf-8")
    if old_local != local_output:
        p.write_text(local_output, encoding="utf-8")
        changed_local = True

    # Clash 远端输出为合法 YAML
    remote_output = (
        f"# 最后更新时间: {now_str()}\n"
        "# 从Surge自动同步\n"
        f"# 原始文件: {p.name}\n"
        "rules:\n"
        + "\n".join(f"  - {rule}" for rule in rules)
        + "\n"
    )

    target = repo / p.name
    old_remote = target.read_text(encoding="utf-8") if target.exists() else None

    if old_remote != remote_output:
        target.write_text(remote_output, encoding="utf-8")
        changed_remote = True

if changed_local:
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
        check=True,
    )
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(
        ["git", "commit", "-m", f"[AUTO_SYNC] 本地格式化 Surge 规则集 - {now_str()}"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "remote",
            "set-url",
            "origin",
            f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/USNOCTURNE90/Surge.git",
        ],
        check=True,
    )
    subprocess.run(["git", "push"], check=True)

if changed_remote:
    subprocess.run(["git", "-C", "clash_repo", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        ["git", "-C", "clash_repo", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
        check=True,
    )
    subprocess.run(["git", "-C", "clash_repo", "add", "."], check=True)
    subprocess.run(
        ["git", "-C", "clash_repo", "commit", "-m", f"[AUTO_SYNC] 从Surge自动同步规则集 - {now_str()}"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            "clash_repo",
            "remote",
            "set-url",
            "origin",
            f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/{os.environ['TARGET_REPO']}.git",
        ],
        check=True,
    )
    subprocess.run(["git", "-C", "clash_repo", "push"], check=True)