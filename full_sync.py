import os, re, subprocess, json, ipaddress, shutil
from pathlib import Path
from datetime import datetime, timedelta

def get_time(): return (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

def process_line(line):
    line = line.strip()
    if not line or line.startswith("#"): return line
    prefixes = ["DOMAIN-SUFFIX,", "DOMAIN-KEYWORD,", "DOMAIN,", "IP-CIDR,", "IP-ASN,", "PROCESS-NAME,"]
    if any(line.upper().startswith(p) for p in prefixes): return line
    if "." in line:
        try:
            parts = line.split('.')
            if all(p.isdigit() for p in parts): return f"IP-CIDR,{line}/32"
            return f"DOMAIN-SUFFIX,{line}"
        except: return f"DOMAIN-SUFFIX,{line}"
    return f"PROCESS-NAME,{line}"

def to_sb(lines):
    rd = {"domain":[], "domain_suffix":[], "domain_keyword":[], "ip_cidr":[], "ip_asn":[], "process_name":[]}
    vp = {"DOMAIN":"domain", "DOMAIN-SUFFIX":"domain_suffix", "DOMAIN-KEYWORD":"domain_keyword", "IP-CIDR":"ip_cidr", "IP-CIDR6":"ip_cidr", "IP-ASN":"ip_asn", "PROCESS-NAME":"process_name"}
    for l in lines:
        l = l.strip()
        if not l or l.startswith("#"): continue
        ps = l.split(',')
        px = ps[0].upper()
        if px in vp and len(ps) >= 2: rd[vp[px]].append(ps[1].strip())
        elif re.match(r"^\d+\.\d+\.\d+\.\d+(/\d+)?$", l): rd["ip_cidr"].append(l if "/" in l else f"{l}/32")
        elif "." in l and not any(c in l for c in [":", "/", " "]): rd["domain_suffix"].append(l)
    act = {k: v for k, v in rd.items() if v}
    return {"version": 1, "rules": [act]} if act else None

token = os.environ.get("GITHUB_TOKEN")
root = Path(".")
excludes = ['.git', '.github', 'Clash_Tmp', 'SingBox_Temp', 'LICENSE', 'README.md']

# 针对无后缀文件进行筛选
files = [f for f in root.glob('*') if f.is_file() and f.name not in excludes and f.suffix not in ['.py', '.yml', '.yaml', '.md', '.txt']]

# 清理工作目录
for d in ["Clash_Temp", "SingBox_Temp"]:
    if os.path.exists(d): shutil.rmtree(d)

# 使用标准鉴权方式
c_url = f"https://x-access-token:{token}@github.com/USNOCTURNE90/Clash.git"
s_url = f"https://x-access-token:{token}@github.com/USNOCTURNE90/Sing-Box.git"

subprocess.run(["git", "clone", c_url, "Clash_Temp"], check=True)
subprocess.run(["git", "clone", s_url, "SingBox_Temp"], check=True)

for f_path in files:
    with open(f_path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()
    
    # 更新 Surge 原文件
    new_lines = [f"# 最后更新时间: {get_time()} (北京时间)"]
    for l in raw_lines:
        if not l.startswith("# 最后更新时间:"): new_lines.append(process_line(l))
    with open(f_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))
    
    # 同步 Clash
    clash_data = [f"# 最后更新时间: {get_time()}", "rules:"]
    for nl in new_lines:
        if nl and not nl.startswith("#"): clash_data.append(f"  - {nl}")
    with open(Path("Clash_Temp") / f_path.name, "w", encoding="utf-8") as f:
        f.write("\n".join(clash_data))
    
    # 同步 Sing-Box
    sb_data = to_sb(new_lines)
    if sb_data:
        with open(Path("SingBox_Temp") / f_path.name, "w", encoding="utf-8") as f:
            json.dump(sb_data, f, indent=2, ensure_ascii=False)

def push_repo(path, msg):
    subprocess.run(["git", "-C", path, "add", "."], check=True)
    status = subprocess.run(["git", "-C", path, "status", "--porcelain"], capture_output=True, text=True).stdout
    if status.strip():
        subprocess.run(["git", "-C", path, "config", "user.name", "GitHub Actions Bot"], check=True)
        subprocess.run(["git", "-C", path, "config", "user.email", "actions@github.com"], check=True)
        subprocess.run(["git", "-C", path, "commit", "-m", msg], check=True)
        subprocess.run(["git", "-C", path, "push"], check=True)

push_repo(".", f"[AUTO_FORMAT] {get_time()}")
push_repo("Clash_Temp", f"[AUTO_SYNC] Clash {get_time()}")
push_repo("SingBox_Temp", f"[AUTO_SYNC] Sing-Box {get_time()}")
