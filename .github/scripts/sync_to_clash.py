import os
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta


# 只处理这些后缀；没有后缀的文件也处理
ALLOWED_SUFFIXES = {
    "",
    ".list",
    ".txt",
    ".rules",
    ".rule",
    ".conf",
}

# 跳过这些名字 / 目录
SKIP_NAMES = {
    ".git",
    ".github",
    "README.md",
    "LICENSE",
    ".DS_Store",
}

# 如果你以后把规则文件统一放到某个目录，可以改这里
SOURCE_DIR = Path(".")

# 允许直接原样保留的规则前缀
SUPPORTED_RULE_PREFIXES = (
    "DOMAIN,",
    "DOMAIN-SUFFIX,",
    "DOMAIN-KEYWORD,",
    "DOMAIN-WILDCARD,",
    "IP-CIDR,",
    "IP-CIDR6,",
    "IP-ASN,",
    "PROCESS-NAME,",
    "DST-PORT,",
    "SRC-IP,",
    "SRC-IP-CIDR,",
    "SRC-PORT,",
    "URL-REGEX,",
    "USER-AGENT,",
)

BJ_TZ = timezone(timedelta(hours=8))


def bj_now_str() -> str:
    return datetime.now(BJ_TZ).strftime("%Y-%m-%d %H:%M:%S (北京时间)")


def run(cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, check=True)


def is_ipv4(s: str) -> bool:
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", s):
        return False
    parts = s.split(".")
    return all(0 <= int(x) <= 255 for x in parts)


def is_ipv4_cidr(s: str) -> bool:
    m = re.fullmatch(r"(\d+\.\d+\.\d+\.\d+)/(\d{1,2})", s)
    if not m:
        return False
    ip, mask = m.groups()
    if not is_ipv4(ip):
        return False
    return 0 <= int(mask) <= 32


def is_ipv6_or_cidr(s: str) -> bool:
    # 这里只做宽松识别，避免把 IPv6 误当域名
    return ":" in s


def looks_like_plain_domain(s: str) -> bool:
    # 仅接受“裸域名 / 子域名 / 通配域名”这种简单格式
    # 避免把复杂规则、注释尾巴、带空格内容误判成域名
    s = s.strip()
    if " " in s or "," in s or "/" in s:
        return False
    if s.startswith("http://") or s.startswith("https://"):
        return False
    if s.startswith("*."):
        s = s[2:]
    if s.endswith("."):
        s = s[:-1]
    if "." not in s:
        return False
    return re.fullmatch(r"[A-Za-z0-9.-]+", s) is not None


def normalize_rule(line: str):
    raw = line.strip()

    # 空行 / 注释
    if not raw or raw.startswith("#") or raw.startswith("//") or raw.startswith(";"):
        return None

    # 去掉行尾注释（只处理很常见的情况）
    if " #" in raw:
        raw = raw.split(" #", 1)[0].strip()

    # 已经是支持的规则，直接保留
    if raw.startswith(SUPPORTED_RULE_PREFIXES):
        return raw

    # 纯 IPv4
    if is_ipv4(raw):
        return f"IP-CIDR,{raw}/32"

    # IPv4 CIDR
    if is_ipv4_cidr(raw):
        return f"IP-CIDR,{raw}"

    # 宽松识别 IPv6
    if is_ipv6_or_cidr(raw):
        if "/" in raw:
            return f"IP-CIDR6,{raw}"
        return f"IP-CIDR6,{raw}/128"

    # 裸域名
    if looks_like_plain_domain(raw):
        if raw.startswith("*."):
            return f"DOMAIN-WILDCARD,{raw}"
        return f"DOMAIN-SUFFIX,{raw}"

    # 其他复杂内容一律跳过，不瞎转
    return None


def collect_source_files(base: Path):
    files = []
    for p in base.iterdir():
        if p.name in SKIP_NAMES:
            continue
        if p.is_dir():
            continue
        if p.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        files.append(p)
    return sorted(files, key=lambda x: x.name.lower())


def build_yaml_output(source_name: str, rules: list[str]) -> str:
    lines = [
        f"# 最后更新时间: {bj_now_str()}",
        "# 从Surge自动同步",
        f"# 原始文件: {source_name}",
        "payload:",
    ]
    lines.extend([f"  - {rule}" for rule in rules])
    lines.append("")
    return "\n".join(lines)


def main():
    target_repo = os.environ["TARGET_REPO"]
    target_branch = os.environ["TARGET_BRANCH"]
    github_token = os.environ["GITHUB_TOKEN"]

    repo = Path("clash_repo")
    if repo.exists():
        shutil.rmtree(repo)

    run(
        [
            "git",
            "clone",
            f"https://x-access-token:{github_token}@github.com/{target_repo}.git",
            "clash_repo",
        ]
    )
    run(["git", "-C", "clash_repo", "checkout", target_branch])

    changed = False
    source_files = collect_source_files(SOURCE_DIR)

    if not source_files:
        print("No source files found in repository root.")
        return

    generated_names = set()

    for p in source_files:
        content = p.read_text(encoding="utf-8", errors="ignore").splitlines()

        rules = []
        seen = set()

        for raw in content:
            rule = normalize_rule(raw)
            if not rule:
                continue
            if rule not in seen:
                seen.add(rule)
                rules.append(rule)

        if not rules:
            print(f"Skip empty/unsupported file: {p.name}")
            continue

        # Clash 仓库里统一输出成 .yaml
        target_name = p.stem + ".yaml"
        generated_names.add(target_name)

        out = build_yaml_output(p.name, rules)
        target = repo / target_name
        old = target.read_text(encoding="utf-8") if target.exists() else None

        if old != out:
            target.write_text(out, encoding="utf-8")
            changed = True
            print(f"Updated: {target_name}")

    # 删除由本脚本生成、但源端已不存在的旧 yaml 文件
    for rp in repo.iterdir():
        if not rp.is_file():
            continue
        if rp.name.startswith("."):
            continue
        if rp.suffix.lower() != ".yaml":
            continue

        if rp.name not in generated_names:
            text = rp.read_text(encoding="utf-8", errors="ignore")
            if "# 从Surge自动同步" in text:
                rp.unlink()
                changed = True
                print(f"Deleted stale file: {rp.name}")

    if not changed:
        print("No changes detected.")
        return

    run(["git", "-C", "clash_repo", "config", "user.name", "github-actions[bot]"])
    run(
        [
            "git",
            "-C",
            "clash_repo",
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
        ]
    )

    run(["git", "-C", "clash_repo", "add", "."])

    status = subprocess.run(["git", "-C", "clash_repo", "diff", "--cached", "--quiet"])
    if status.returncode == 0:
        print("Nothing staged after add.")
        return

    run(
        [
            "git",
            "-C",
            "clash_repo",
            "commit",
            "-m",
            f"[AUTO_SYNC] Surge -> Clash {bj_now_str()}",
        ]
    )
    run(["git", "-C", "clash_repo", "push"])
    print("Sync completed.")


if __name__ == "__main__":
    main()
