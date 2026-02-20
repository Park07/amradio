#!/usr/bin/env python3
"""Run from repo root: python3 find_ugl.py"""
import os

REPO_ROOT = os.getcwd()
SKIP_DIRS = {'.git', 'node_modules', 'target', '.next'}

for root, dirs, files in os.walk(REPO_ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for fname in files:
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if 'ugl' in line.lower():
                        rel = os.path.relpath(fpath, REPO_ROOT)
                        print(f"{rel}:{i}:  {line.rstrip()}")
        except:
            pass