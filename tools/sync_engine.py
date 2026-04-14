#!/usr/bin/env python3
import hashlib
import ipaddress
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import yaml

STATE_FILE = '.sync_state.json'
MANAGED_HEADER = '# AUTO_SYNC_MANAGED: true'
RULESET_HEADER_PREFIX = '# RULESET: '
KNOWN_PREFIXES = (
    'DOMAIN,',
    'DOMAIN-SUFFIX,',
    'DOMAIN-KEYWORD,',
    'DOMAIN-WILDCARD,',
    'IP-CIDR,',
    'IP-CIDR6,',
    'IP-ASN,',
    'PROCESS-NAME,',
    'DST-PORT,',
    'SRC-IP,',
    'SRC-IP-CIDR,',
    'SRC-PORT,',
    'URL-REGEX,',
    'USER-AGENT,',
)
NOISE_PREFIXES = (
    '最后更新时间',
    '从Clash自动标准化',
    '从Clash自动同步',
    '从Surge自动同步',
    '原始文件:',
    '规则集:',
)
TYPE_ORDER = {
    'PROCESS-NAME': 10,
    'DOMAIN': 20,
    'DOMAIN-SUFFIX': 30,
    'DOMAIN-KEYWORD': 40,
    'DOMAIN-WILDCARD': 50,
    'IP-CIDR': 60,
    'IP-CIDR6': 70,
    'IP-ASN': 80,
    'SRC-IP': 90,
    'SRC-IP-CIDR': 100,
    'SRC-PORT': 110,
    'DST-PORT': 120,
    'URL-REGEX': 130,
    'USER-AGENT': 140,
}
DOMAIN_RE = re.compile(r'^(?=.{1,253}$)([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$')
WILDCARD_RE = re.compile(r'^\*\.(?=.{1,253}$)([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$')
PROCESS_RE = re.compile(r'^[A-Za-z0-9_.+\-]{1,128}$')


def run(cmd: List[str], cwd: Optional[Path] = None) -> str:
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f'Command failed: {cmd}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}')
    return result.stdout.strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def canonical_hash(rules: List[str]) -> str:
    return 'sha256:' + sha256_text('\n'.join(rules))


def load_state(root: Path) -> dict:
    path = root / STATE_FILE
    if not path.exists():
        return {'version': 1, 'managed_rulesets': {}}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {'version': 1, 'managed_rulesets': {}}


def save_state(root: Path, state: dict) -> None:
    path = root / STATE_FILE
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def is_noise_line(s: str) -> bool:
    t = s.strip()
    if not t:
        return True
    if t.startswith('#'):
        return True
    if t in ('payload:', 'rules:'):
        return True
    for p in NOISE_PREFIXES:
        if t.startswith(p):
            return True
    return False


def normalize_rule(line: str) -> Optional[str]:
    raw = line.strip()
    if not raw:
        return None
    if raw.startswith('#'):
        return None
    for p in KNOWN_PREFIXES:
        if raw.upper().startswith(p):
            return raw
    try:
        ip = ipaddress.ip_address(raw)
        if isinstance(ip, ipaddress.IPv4Address):
            return f'IP-CIDR,{raw}/32'
        return f'IP-CIDR6,{raw}/128'
    except ValueError:
        pass
    try:
        net = ipaddress.ip_network(raw, strict=False)
        if isinstance(net, ipaddress.IPv4Network):
            return f'IP-CIDR,{raw}'
        return f'IP-CIDR6,{raw}'
    except ValueError:
        pass
    if WILDCARD_RE.fullmatch(raw):
        return f'DOMAIN-WILDCARD,{raw}'
    if DOMAIN_RE.fullmatch(raw):
        return f'DOMAIN-SUFFIX,{raw}'
    if PROCESS_RE.fullmatch(raw):
        return f'PROCESS-NAME,{raw}'
    return raw


def stable_rules(rules: List[str]) -> List[str]:
    deduped = []
    seen = set()
    for r in rules:
        if not r:
            continue
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    def keyfunc(rule: str):
        prefix = rule.split(',', 1)[0].upper() if ',' in rule else 'ZZZ_UNKNOWN'
        return (TYPE_ORDER.get(prefix, 9999), rule)
    return sorted(deduped, key=keyfunc)


def extract_candidate_rules_from_text(content: str) -> List[str]:
    out = []
    for line in content.splitlines():
        t = line.strip()
        if not t:
            continue
        if is_noise_line(t):
            continue
        if t.startswith('- '):
            t = t[2:].strip()
        out.append(t)
    return out


def parse_surge_file(content: str) -> List[str]:
    rules = []
    for c in extract_candidate_rules_from_text(content):
        n = normalize_rule(c)
        if n:
            rules.append(n)
    return stable_rules(rules)


def parse_clash_file(content: str) -> List[str]:
    candidates: List[str] = []
    try:
        obj = yaml.safe_load(content)
        if isinstance(obj, dict):
            payload = None
            if isinstance(obj.get('payload'), list):
                payload = obj['payload']
            elif isinstance(obj.get('rules'), list):
                payload = obj['rules']
            if payload is not None:
                for item in payload:
                    if isinstance(item, str):
                        candidates.append(item.strip())
    except Exception:
        pass
    if not candidates:
        candidates = extract_candidate_rules_from_text(content)
    rules = []
    for c in candidates:
        n = normalize_rule(c)
        if n:
            rules.append(n)
    return stable_rules(rules)


def render_surge(stem: str, rules: List[str]) -> str:
    lines = [MANAGED_HEADER, f'{RULESET_HEADER_PREFIX}{stem}', '', *rules, '']
    return '\n'.join(lines)


def render_clash(stem: str, rules: List[str]) -> str:
    lines = [MANAGED_HEADER, f'{RULESET_HEADER_PREFIX}{stem}', 'payload:']
    lines.extend([f'  - {r}' for r in rules])
    lines.append('')
    return '\n'.join(lines)


def detect_rule_dir(root: Path, repo_type: str) -> Path:
    candidates = ['rules', 'Rules', 'rule', 'Rule', 'ruleset', 'RuleSet']
    for name in candidates:
        p = root / name
        if p.is_dir():
            return p
    fallback = root / ('rules' if repo_type == 'surge' else 'ruleset')
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def scan_surge_rules(rule_dir: Path) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    for p in rule_dir.iterdir():
        if not p.is_file() or p.name.startswith('.'):
            continue
        if p.suffix:
            continue
        if p.name in (STATE_FILE,):
            continue
        if p.name in out:
            raise RuntimeError(f'Duplicate Surge ruleset stem: {p.name}')
        out[p.name] = p
    return out


def resolve_clash_ruleset_files(rule_dir: Path) -> Dict[str, Path]:
    by_key: Dict[str, List[Path]] = {}
    for p in rule_dir.iterdir():
        if not p.is_file() or p.name.startswith('.'):
            continue
        if p.name == STATE_FILE:
            continue
        if p.suffix == '':
            key = p.name
        elif p.suffix == '.yaml':
            key = p.stem
        else:
            continue
        by_key.setdefault(key, []).append(p)
    resolved: Dict[str, Path] = {}
    for key, items in by_key.items():
        if len(items) > 1:
            raise RuntimeError(f'Conflicting Clash ruleset files for stem {key}: {[str(x) for x in items]}')
        resolved[key] = items[0]
    return resolved


def parse_repo_rules(root: Path, repo_type: str) -> Dict[str, List[str]]:
    rule_dir = detect_rule_dir(root, repo_type)
    files = scan_surge_rules(rule_dir) if repo_type == 'surge' else resolve_clash_ruleset_files(rule_dir)
    out: Dict[str, List[str]] = {}
    for stem, path in files.items():
        content = path.read_text(encoding='utf-8')
        rules = parse_surge_file(content) if repo_type == 'surge' else parse_clash_file(content)
        if content.strip() and not rules:
            raise RuntimeError(f'Parse produced empty rules for existing non-empty file: {path}')
        out[stem] = rules
    return out


def write_if_changed(path: Path, content: str) -> bool:
    old = path.read_text(encoding='utf-8') if path.exists() else None
    if old == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return True


def is_managed_file(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        head = path.read_text(encoding='utf-8').splitlines()[:3]
    except Exception:
        return False
    return any(MANAGED_HEADER in line for line in head)


def update_state_for_rulesets(state: dict, rulesets: Dict[str, List[str]], current_repo_type: str, current_rule_dir: Path, peer_rule_dir: Path) -> None:
    managed = state.setdefault('managed_rulesets', {})
    for stem, rules in rulesets.items():
        entry = managed.setdefault(stem, {'managed_by_system': True})
        entry['managed_by_system'] = True
        entry['surge_path'] = str((current_rule_dir / stem).as_posix()) if current_repo_type == 'surge' else str((peer_rule_dir / stem).as_posix())
        entry['clash_path'] = str((peer_rule_dir / stem).as_posix()) if current_repo_type == 'surge' else str((current_rule_dir / stem).as_posix())
        entry['last_rule_hash'] = canonical_hash(rules)
        entry['last_synced_from'] = current_repo_type


def apply_sync_to_peer(source_rulesets: Dict[str, List[str]], peer_root: Path, peer_type: str, state: dict) -> None:
    peer_rule_dir = detect_rule_dir(peer_root, peer_type)
    for stem, rules in source_rulesets.items():
        target = peer_rule_dir / stem
        content = render_surge(stem, rules) if peer_type == 'surge' else render_clash(stem, rules)
        write_if_changed(target, content)
        legacy_yaml = peer_rule_dir / f'{stem}.yaml'
        if peer_type == 'clash' and legacy_yaml.exists() and legacy_yaml != target:
            legacy_yaml.unlink()
    managed = state.get('managed_rulesets', {})
    source_stems = set(source_rulesets.keys())
    deletion_candidates = []
    for stem, meta in managed.items():
        if stem in source_stems:
            continue
        target_rel = meta.get('surge_path') if peer_type == 'surge' else meta.get('clash_path')
        if not target_rel:
            continue
        abs_target = peer_root / target_rel
        if abs_target.exists() and is_managed_file(abs_target):
            deletion_candidates.append((stem, abs_target))
    total_managed = max(len(managed), 1)
    if len(deletion_candidates) > 5 or (len(deletion_candidates) / total_managed) > 0.2:
        raise RuntimeError('Deletion fuse triggered; aborting potentially unsafe bulk deletion')
    for _, path in deletion_candidates:
        path.unlink()


def commit_and_push_peer(peer_root: Path, peer_branch: str, commit_message: str) -> None:
    run(['git', 'config', 'user.name', 'autosync-bot'], cwd=peer_root)
    run(['git', 'config', 'user.email', 'autosync-bot@users.noreply.github.com'], cwd=peer_root)
    run(['git', 'add', '.sync_state.json'], cwd=peer_root)
    run(['git', 'add', '-u'], cwd=peer_root)
    status = run(['git', 'status', '--porcelain'], cwd=peer_root)
    if not status.strip():
        return
    run(['git', 'commit', '-m', commit_message], cwd=peer_root)
    run(['git', 'push', 'origin', f'HEAD:{peer_branch}'], cwd=peer_root)


def main() -> None:
    current_repo_type = os.environ['CURRENT_REPO_TYPE'].strip().lower()
    peer_repo = os.environ['PEER_REPO'].strip()
    peer_branch = os.environ['PEER_BRANCH'].strip()
    gh_pat = os.environ['GH_PAT'].strip()
    current_root = Path.cwd()
    peer_type = 'clash' if current_repo_type == 'surge' else 'surge'
    runner_temp = Path(os.environ.get('RUNNER_TEMP', '/tmp'))
    peer_root = runner_temp / 'peer_repo_sync'
    if peer_root.exists():
        run(['rm', '-rf', str(peer_root)])
    run(['git', 'clone', f'https://x-access-token:{gh_pat}@github.com/{peer_repo}.git', str(peer_root)])
    run(['git', 'checkout', peer_branch], cwd=peer_root)
    run(['git', 'remote', 'set-url', 'origin', f'https://x-access-token:{gh_pat}@github.com/{peer_repo}.git'], cwd=peer_root)

    current_state = load_state(current_root)
    peer_state = load_state(peer_root)
    state = {'version': 1, 'managed_rulesets': {}}
    state['managed_rulesets'].update(peer_state.get('managed_rulesets', {}))
    state['managed_rulesets'].update(current_state.get('managed_rulesets', {}))

    current_rule_dir = detect_rule_dir(current_root, current_repo_type)
    peer_rule_dir = detect_rule_dir(peer_root, peer_type)
    current_rulesets = parse_repo_rules(current_root, current_repo_type)
    if not current_rulesets:
        raise RuntimeError('No rulesets detected in current repository; aborting to avoid dangerous empty sync')

    apply_sync_to_peer(current_rulesets, peer_root, peer_type, state)
    update_state_for_rulesets(state, current_rulesets, current_repo_type, current_rule_dir, peer_rule_dir)
    save_state(current_root, state)
    save_state(peer_root, state)
    commit_and_push_peer(peer_root, peer_branch, f'[AUTO_SYNC] Sync rulesets from {current_repo_type} to {peer_type}')

if __name__ == '__main__':
    main()
