name: Convert Surge Rules to Clash

on:
  push:
    paths:
      - 'rules/**/*.list'
  workflow_dispatch:

jobs:
  convert:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout Surge repository
        uses: actions/checkout@v3

      - name: Checkout Clash repository
        uses: actions/checkout@v3
        with:
          repository: USNOCTURNE90/Clash-auto
          token: ${{ secrets.PAT }}
          path: clash-auto

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Debug Info
        run: |
          echo "Current directory:"
          pwd
          echo "Directory contents:"
          ls -la
          echo "GitHub workspace:"
          echo $GITHUB_WORKSPACE

      - name: Convert Rules
        run: |
          python .github/workflows/convert-rules.py
        env:
          SURGE_RULES_PATH: rules
          CLASH_RULES_PATH: clash-auto/rules

      - name: Commit and push changes
        run: |
          cd clash-auto
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add rules/
          git commit -m "chore: sync rules from surge repository" || echo "No changes to commit"
          git push origin main
