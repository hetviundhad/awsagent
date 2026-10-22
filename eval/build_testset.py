"""
eval/build_testset.py
Curates and builds the evaluation testset (65 in-scope + 16 off-material = 81 items)
grounded directly in the active course's real ingested documents and chunks.
Never uses hardcoded algorithm demo texts.
"""

import json
import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath("."))
from eval.seed_bank_and_testset import seed_bank_and_testset

def build_testset(output_path: str = "eval/testset.json") -> List[Dict[str, Any]]:
    seed_bank_and_testset()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    build_testset()
