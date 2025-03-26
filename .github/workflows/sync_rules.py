name: Sync Rules

on:
  push:
    branches:
      - main
      - master
      - Surge  # 添加可能的分支名称
    paths:
      - '**'
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v2
        with:
          token: ${{ secrets.PAT }}
          
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.x'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          
      - name: Configure Git
        run: |
          git config --global user.name "GitHub Actions Bot"
          git config --global user.email "actions@github.com"
          
      - name: Debug environment
        run: |
          echo "Current directory:"
          pwd
          echo "Directory contents:"
          ls -la
          echo "Workflows directory contents:"
          ls -la .github/workflows/
          echo "Python version:"
          python --version
          
      - name: Create sync script
        run: |
          cat > sync_rules.py << 'EOL'
          #!/usr/bin/env python3
          # -*- coding: utf-8 -*-

          import os
          import re
          import time
          import subprocess
          from pathlib import Path
          import logging
          import traceback
          from typing import List, Dict, Tuple

          # 配置日志
          logging.basicConfig(
              level=logging.INFO,
              format='%(asctime)s - %(levelname)s - %(message)s'
          )
          logger = logging.getLogger(__name__)

          class RuleConverter:
              def __init__(self):
                  self.surge_dir = Path(".")  # 直接使用仓库根目录
                  self.clash_dir = Path("Clash")
                  
                  # 使用带认证的 URL 进行 Git 操作
                  github_token = os.environ.get("GITHUB_TOKEN", "")
                  if github_token:
                      logger.info("使用 GITHUB_TOKEN 进行认证")
                      self.clash_repo = f"https://{github_token}@github.com/USNOCTURNE90/Clash-auto.git"
                  else:
                      logger.warning("未找到 GITHUB_TOKEN 环境变量，将使用匿名克隆")
                      self.clash_repo = "https://github.com/USNOCTURNE90/Clash-auto.git"
                  
              def convert_surge_to_clash(self, surge_content: str) -> str:
                  """将 Surge 规则转换为 Clash 格式"""
                  # 添加 rules: 头部
                  clash_rules = ["rules:"]
                  
                  # 处理每一行规则
                  for line in surge_content.split('\n'):
                      line = line.strip()
                      if not line or line.startswith('#'):
                          continue
                          
                      # 转换规则格式
                      if line.startswith('DOMAIN-SUFFIX,'):
                          clash_rules.append(f"  - {line}")
                      elif line.startswith('DOMAIN-KEYWORD,'):
                          clash_rules.append(f"  - {line}")
                      elif line.startswith('DOMAIN,'):
                          clash_rules.append(f"  - {line}")
                      elif line.startswith('IP-CIDR,'):
                          clash_rules.append(f"  - {line}")
                      elif line.startswith('IP-ASN,'):
                          clash_rules.append(f"  - {line}")
                      elif line.startswith('PROCESS-NAME,'):
                          clash_rules.append(f"  - {line}")
                          
                  return '\n'.join(clash_rules)
                  
              def sync_rules(self):
                  """同步规则集到 Clash 仓库"""
                  try:
                      # 打印当前工作目录和文件列表
                      logger.info(f"当前工作目录: {os.getcwd()}")
                      logger.info(f"目录内容: {list(Path('.').glob('*'))}")
                      
                      # 清理 Clash 目录（如果存在）
                      if self.clash_dir.exists():
                          import shutil
                          logger.info(f"清理已存在的 Clash 目录: {self.clash_dir}")
                          shutil.rmtree(self.clash_dir)
                      
                      # 克隆 Clash 仓库
                      logger.info(f"正在克隆 Clash 仓库: {self.clash_repo}")
                      result = subprocess.run(['git', 'clone', self.clash_repo, 'Clash'], 
                                             capture_output=True, text=True)
                      if result.returncode != 0:
                          logger.error(f"克隆失败: {result.stderr}")
                          # 尝试不使用令牌克隆
                          logger.info("尝试使用公开URL克隆...")
                          result = subprocess.run(['git', 'clone', "https://github.com/USNOCTURNE90/Clash-auto.git", 'Clash'], 
                                                capture_output=True, text=True)
                          if result.returncode != 0:
                              logger.error(f"公开URL克隆也失败: {result.stderr}")
                              return
                      
                      # 寻找规则文件
                      rule_files = []
                      # 查找可能是规则文件的所有文件
                      for surge_file in self.surge_dir.glob('*'):
                          if not surge_file.is_file() or surge_file.name.startswith('.') or surge_file.name in ["sync_rules.py", "sync_rules.yml"]:
                              continue
                          # 不再过滤关键词，而是查看文件内容
                          try:
                              with open(surge_file, 'r', encoding='utf-8') as f:
                                  content = f.read()
                                  if "DOMAIN" in content or "IP-CIDR" in content:
                                      rule_files.append(surge_file)
                          except Exception as e:
                              logger.warning(f"无法读取文件 {surge_file.name}: {str(e)}")
                      
                      if not rule_files:
                          logger.warning("未找到规则文件！检查当前目录。")
                          logger.info(f"当前目录中的所有文件: {list(Path('.').glob('*'))}")
                          return
                          
                      logger.info(f"找到 {len(rule_files)} 个规则文件: {[f.name for f in rule_files]}")
                      
                      # 遍历规则文件
                      for surge_file in rule_files:
                          try:
                              # 读取 Surge 规则
                              with open(surge_file, 'r', encoding='utf-8') as f:
                                  surge_content = f.read()
                              
                              # 转换为 Clash 格式
                              clash_content = self.convert_surge_to_clash(surge_content)
                              
                              # 写入 Clash 规则文件
                              clash_file = self.clash_dir / surge_file.name
                              with open(clash_file, 'w', encoding='utf-8') as f:
                                  f.write(clash_content)
                                  
                              logger.info(f"已同步规则集: {surge_file.name}")
                          except Exception as e:
                              logger.error(f"处理文件 {surge_file.name} 时出错: {str(e)}")
                              traceback.print_exc()
                      
                      # 提交更改到 Clash 仓库
                      logger.info("添加更改到Git暂存区...")
                      result = subprocess.run(['git', '-C', 'Clash', 'add', '.'], 
                                             capture_output=True, text=True)
                      if result.returncode != 0:
                          logger.error(f"添加文件失败: {result.stderr}")
                          return
                      
                      # 检查是否有更改
                      logger.info("检查是否有更改...")
                      result = subprocess.run(['git', '-C', 'Clash', 'status', '--porcelain'], 
                                             capture_output=True, text=True)
                      
                      if result.stdout.strip():
                          logger.info("发现更改，准备提交...")
                          commit_message = f"自动同步规则集 - {time.strftime('%Y-%m-%d %H:%M:%S')}"
                          result = subprocess.run(['git', '-C', 'Clash', 'commit', '-m', commit_message], 
                                                 capture_output=True, text=True)
                          if result.returncode != 0:
                              logger.error(f"提交更改失败: {result.stderr}")
                              return
                          
                          logger.info("推送更改到远程仓库...")
                          result = subprocess.run(['git', '-C', 'Clash', 'push'], 
                                                 capture_output=True, text=True)
                          if result.returncode != 0:
                              logger.error(f"推送更改失败: {result.stderr}")
                              return
                          
                          logger.info("已成功提交更改到 Clash 仓库")
                      else:
                          logger.info("没有需要提交的更改")
                          
                  except Exception as e:
                      logger.error(f"同步规则集时出错: {str(e)}")
                      traceback.print_exc()

          def main():
              logger.info("开始执行同步脚本...")
              try:
                  converter = RuleConverter()
                  converter.sync_rules()
                  logger.info("同步脚本执行完成")
              except Exception as e:
                  logger.error(f"执行脚本时出错: {str(e)}")
                  traceback.print_exc()

          if __name__ == "__main__":
              main()
          EOL
          chmod +x sync_rules.py
          
      - name: Run sync script with verbose output
        run: python sync_rules.py
        env:
          GITHUB_TOKEN: ${{ secrets.PAT }}
