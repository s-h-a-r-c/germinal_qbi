#!/usr/bin/env python
import os
import sys
import subprocess
from typing import List

def print_status(prefix: str, msg: str) -> None:
    print(f"[{prefix}] {msg}")

def try_import(pkg: str) -> bool:
    try:
        __import__(pkg)
        return True
    except Exception as e:
        print_status("ERROR", f"Import failed: {pkg}: {e}")
        return False

def cmd_ok(cmd: List[str]) -> bool:
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception as e:
        print_status("WARN", f"Command failed: {' '.join(cmd)} -> {e}")
        return False

def main() -> int:
    required = [
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "yaml",
        "filelock",
        "omegaconf",
        "mdtraj",
        "Bio",
        "tqdm",
    ]
    print_status("INFO", "Checking Python imports")
    missing = [p for p in required if not try_import(p)]
    if missing:
        print_status("ERROR", f"Missing packages: {', '.join(missing)}")
        return 1

    print_status("INFO", "Checking GPU availability via nvidia-smi (optional)")
    if cmd_ok(["nvidia-smi"]):
        print_status("OK", "nvidia-smi detected")
    else:
        print_status("WARN", "nvidia-smi not available; GPU features may be disabled")

    print_status("INFO", "Checking JAX device")
    try:
        import jax
        device = jax.default_backend()
        print_status("OK", f"JAX backend: {device}")
    except Exception as e:
        print_status("WARN", f"JAX check failed: {e}")

    print_status("INFO", "Checking PyTorch CUDA")
    try:
        import torch
        print_status("OK", f"Torch: {torch.__version__}; CUDA available: {torch.cuda.is_available()}")
    except Exception as e:
        print_status("WARN", f"Torch check failed: {e}")

    print_status("INFO", "Checking local packages")
    for mod in ["colabdesign", "germinal"]:
        if try_import(mod):
            print_status("OK", f"Imported {mod}")
        else:
            return 2

    print_status("INFO", "Checking PyRosetta (optional)")
    try:
        import pyrosetta  # type: ignore
        print_status("OK", "PyRosetta available")
    except Exception:
        print_status(
            "WARN",
            "PyRosetta not found. If you have a licensed build, install via: \n"
            "  bash scripts/install_env.sh --pyrosetta /path/to/pyrosetta.whl\n"
            "See README for details."
        )

    print_status("INFO", "Checking freesasa (optional, required for --proteinmaxx)")
    try:
        import freesasa  # type: ignore
        print_status("OK", "freesasa available")
    except Exception:
        print_status("WARN", "freesasa not found. Install via: pip install freesasa")

    print_status("OK", "All checks passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())

