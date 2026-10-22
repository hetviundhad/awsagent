import os
import re
import pytest

def test_no_float_literals_in_bkt_and_engine():
    """
    Magic numbers rule:
    Fails if bkt.py or engine.py contain numeric float literals outside config.py.
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_files = [
        os.path.join(root_dir, "backend", "app", "learner", "bkt.py"),
        os.path.join(root_dir, "backend", "app", "rag", "engine.py")
    ]
    
    float_pattern = re.compile(r'(?<![a-zA-Z0-9_])\d+\.\d+(?![a-zA-Z0-9_])')
    violations = []

    for file_path in target_files:
        assert os.path.isfile(file_path), f"File not found: {file_path}"
        with open(file_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                # Strip comments
                code_part = line.split("#")[0]
                matches = float_pattern.findall(code_part)
                if matches:
                    violations.append(f"{os.path.basename(file_path)}:{line_no} contains float literal {matches}: {line.strip()}")

    assert not violations, "Found float literals outside config.py:\n" + "\n".join(violations)
