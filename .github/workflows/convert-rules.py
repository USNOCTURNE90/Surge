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
        with:
          path: surge-repo

      - name: Checkout Clash repository
        uses: actions/checkout@v3
        with:
          repository: USNOCTURNE90/Clash-auto
          token: ${{ secrets.PAT }}
          path: clash-repo

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Debug working directory
        run: |
          pwd
          ls -la surge-repo
          ls -la

      - name: Convert Rules
        run: |
          cd surge-repo
          python convert-rules.py
        env:
          SURGE_RULES_PATH: rules
          CLASH_RULES_PATH: ../clash-repo/rules

      - name: List converted files
        run: |
          echo "Converted files in clash-repo:"
          ls -R clash-repo/rules || echo "Rules directory not found"

      - name: Commit and push changes
        run: |
          cd clash-repo
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add rules/
          git commit -m "chore: sync rules from surge repository" || echo "No changes to commit"
          git push origin main
