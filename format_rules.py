#!/usr/bin/env python3

import os
import re
import time
import subprocess
from pathlib import Path
import logging
import traceback
from datetime import datetime, timedelta
import ipaddress

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 获取中国时间
def get_china_time():
    utc_now = datetime.utcnow()
    china_time = utc_now + timedelta(hours=8)
    return china_time.strftime('%Y-%m-%d %H:%M:%S')

# 检查和处理规则行
def process_rule_line(line, is_surge=True):
    line = line.strip()
    if not line or line.startswith("#"):
        return line
    
    # 检查是否已有前缀
    known_prefixes = ["DOMAIN-SUFFIX,", "DOMAIN-KEYWORD,", "DOMAIN,", "IP-CIDR,", "IP-ASN,", "PROCESS-NAME,"]
    if any(line.startswith(prefix) for prefix in known_prefixes):
        return line if is_surge else f"- {line}"
        
    # 检查是否是域名（包含点）
    if "." in line:
        try:
            # 检查是否是纯数字IP
            parts = line.split('.')
            if all(part.isdigit() for part in parts):
                # 尝试解析为IP地址
                ipaddress.ip_address(line)
                # 如果是有效IP，添加IP-CIDR前缀和/32
                return f"IP-CIDR,{line}/32" if is_surge else f"- IP-CIDR,{line}/32"
            else:
                # 是域名，添加DOMAIN-SUFFIX前缀
                return f"DOMAIN-SUFFIX,{line}" if is_surge else f"- DOMAIN-SUFFIX,{line}"
        except ValueError:
            # 不是有效IP，当作域名处理
            return f"DOMAIN-SUFFIX,{line}" if is_surge else f"- DOMAIN-SUFFIX,{line}"
    else:
        # 没有点，作为进程名处理
        return f"PROCESS-NAME,{line}" if is_surge else f"- PROCESS-NAME,{line}"

# 打印当前工作目录和内容
print(f"Current directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")

try:
    # 设置目录
    root_dir = Path(".")
    
    # 要排除的文件和目录
    exclude_patterns = [
        '.git', '.github', 'Clash', '*.yml', '*.yaml', '*.py', '*.md', 
        '.gitignore', 'LICENSE', 'README*'
    ]
    
    def should_exclude(path):
        """判断文件是否应被排除处理"""
        path_str = str(path)
        
        # 排除目录
        if path.is_dir():
            return True
            
        # 排除隐藏文件
        if path.name.startswith('.'):
            return True
            
        # 排除工作流和脚本文件
        for pattern in exclude_patterns:
            if '*' in pattern:
                suffix = pattern.replace('*', '')
                if path_str.endswith(suffix):
                    return True
            elif pattern in path_str:
                return True
        
        return False
    
    # 查找规则文件
    rule_files = []
    for file_path in root_dir.glob('*'):
        if should_exclude(file_path):
            print(f"Skipping excluded file: {file_path}")
            continue
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "DOMAIN" in content or "IP-CIDR" in content or "." in content:
                    rule_files.append(file_path)
                    print(f"Found rule file: {file_path.name}")
        except Exception as e:
            print(f"Error reading {file_path.name}: {str(e)}")
    
    if not rule_files:
        print("No rule files found!")
        print(f"All files: {[f.name for f in root_dir.glob('*') if not should_exclude(f)]}")
        exit(1)
    
    # 处理规则文件
    for rule_file in rule_files:
        with open(rule_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查文件是否已经有规则前缀
        has_prefixes = any(prefix in content for prefix in ["DOMAIN-SUFFIX,", "DOMAIN-KEYWORD,", "DOMAIN,", "IP-CIDR,", "IP-ASN,", "PROCESS-NAME,"])
        
        # 添加最后更新时间标记到文件内容
        current_time = get_china_time()
        content_lines = content.splitlines()
        updated_lines = []
        
        # 更新或添加最后更新时间注释
        time_comment_found = False
        rules_section = False
        
        for line in content_lines:
            if line.startswith("# 最后更新时间:"):
                updated_lines.append(f"# 最后更新时间: {current_time} (北京时间)")
                time_comment_found = True
            elif line.strip() == "rules:" or line.strip() == "payload:":
                rules_section = True
                updated_lines.append(line)
            elif rules_section and line.strip() and not line.startswith("#"):
                # 处理规则部分
                # 去除可能的前缀标记
                if line.strip().startswith("  - "):
                    rule_part = line.strip()[4:]
                elif line.strip().startswith("- "):
                    rule_part = line.strip()[2:]
                else:
                    rule_part = line.strip()
                    
                # 检查是否已有规则前缀
                if not any(rule_part.startswith(prefix) for prefix in ["DOMAIN-SUFFIX,", "DOMAIN-KEYWORD,", "DOMAIN,", "IP-CIDR,", "IP-ASN,", "PROCESS-NAME,"]):
                    # 添加适当的规则前缀
                    processed_line = process_rule_line(rule_part, is_surge=True)
                    updated_lines.append(processed_line)
                else:
                    # 已有规则前缀，保持不变
                    updated_lines.append(rule_part)
            else:
                # 处理非规则部分或注释
                if line.strip() and not line.startswith("#") and not rules_section:
                    # 可能是没有规则标记的普通规则
                    # 检查是否已有规则前缀
                    if not any(line.strip().startswith(prefix) for prefix in ["DOMAIN-SUFFIX,", "DOMAIN-KEYWORD,", "DOMAIN,", "IP-CIDR,", "IP-ASN,", "PROCESS-NAME,"]):
                        # 添加适当的规则前缀
                        processed_line = process_rule_line(line.strip(), is_surge=True)
                        updated_lines.append(processed_line)
                    else:
                        # 已有规则前缀，保持不变
                        updated_lines.append(line)
                else:
                    # 注释或空行
                    updated_lines.append(line)
        
        if not time_comment_found:
            # 在文件开头添加更新时间
            updated_lines.insert(0, f"# 最后更新时间: {current_time} (北京时间)")
        
        # 更新文件内容
        updated_content = "\n".join(updated_lines)
        
        # 只有当内容有变化时才写入文件
        if content != updated_content:
            with open(rule_file, "w", encoding="utf-8") as f:
                f.write(updated_content)
            print(f"Updated rule file: {rule_file.name}")
      
    # 提交更改到当前仓库
    subprocess.run(["git", "add", "."], check=True)
    
    # 检查是否有更改
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True
    )
    
    if result.stdout.strip():
        print("Changes found in current repo, committing...")
        china_time = get_china_time()
        commit_message = f"[AUTO_FORMAT] 自动格式化规则集 - {china_time} (北京时间)"
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            check=True
        )
        
        print("Pushing changes to current repo...")
        subprocess.run(["git", "push"], check=True)
        print("Successfully updated current repo")
    else:
        print("No changes to commit in current repo")
    
    # 获取GitHub令牌
    github_token = os.environ.get("GITHUB_TOKEN", "")
    clash_repo = f"https://{github_token}@github.com/USNOCTURNE90/Clash.git"
    
    # 克隆Clash仓库
    clash_dir = Path("Clash")
    if clash_dir.exists():
        import shutil
        shutil.rmtree(clash_dir)
    
    print(f"Cloning Clash repo: {clash_repo}")
    subprocess.run(["git", "clone", clash_repo, "Clash"], check=True)
    
    # 处理规则文件并同步到Clash仓库
    for rule_file in rule_files:
        with open(rule_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 转换为Clash格式
        clash_rules = []
        comment_lines = []
        
        # 提取注释和规则
        for line in content.splitlines():
            if line.startswith("#"):
                comment_lines.append(line)
            else:
                # 处理规则行（转换为Clash格式）
                processed_line = process_rule_line(line, is_surge=False)
                if processed_line and not processed_line.startswith("#"):
                    clash_rules.append(processed_line)
        
        # 创建Clash YAML格式内容
        current_time = get_china_time()
        clash_content = []
        
        # 添加Clash文件头
        clash_content.append("payload:")
        
        # 添加注释（作为YAML注释）
        for comment in comment_lines:
            if not ("最后更新时间" in comment or "自动同步" in comment or "原始文件" in comment or "规则自动格式化" in comment):
                clash_content.append(f"# {comment[2:].strip() if comment.startswith('# ') else comment}")
        
        # 添加同步信息
        clash_content.append(f"# 从Surge自动同步 - {current_time} (北京时间)")
        clash_content.append(f"# 原始文件: {rule_file.name}")
        
        # 添加规则
        for rule in clash_rules:
            clash_content.append(f"  {rule}")
        
        # 完整的Clash内容
        clash_yaml = "\n".join(clash_content)
        
        # 写入Clash规则文件
        clash_file = clash_dir / rule_file.name
        with open(clash_file, "w", encoding="utf-8") as f:
            f.write(clash_yaml)
        
        print(f"Synced rule file to Clash: {rule_file.name}")
    
    # 提交Clash仓库更改
    subprocess.run(["git", "-C", "Clash", "add", "."], check=True)
    
    # 检查是否有更改
    result = subprocess.run(
        ["git", "-C", "Clash", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True
    )
    
    if result.stdout.strip():
        print("Changes found in Clash repo, committing...")
        china_time = get_china_time()
        commit_message = f"[AUTO_SYNC] 从Surge自动同步规则集 - {china_time} (北京时间)"
        subprocess.run(
            ["git", "-C", "Clash", "commit", "-m", commit_message],
            check=True
        )
        
        print("Pushing changes to Clash repo...")
        subprocess.run(["git", "-C", "Clash", "push"], check=True)
        print("Successfully synced rules to Clash repo")
    else:
        print("No changes to commit in Clash repo")

except Exception as e:
    print(f"Error: {str(e)}")
    traceback.print_exc()
    exit(1)
