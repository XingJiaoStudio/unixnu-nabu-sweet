#!/usr/bin/env python3
"""UniXNU ADT step for nabu (Xiaomi Pad 5, SM8150).

nabu is the same SM8150 silicon as guacamole/raphael; only the board
compatible string and the panel resolution differ (1600x2560). The UniXNU
payload driver passes generic ADT flags; the nabu hardware profile in
mkadt.py owns those values.
"""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dram-size", default="0xc0000000")
    parser.add_argument("--owned-memory-size", type=lambda value: int(value, 0))
    parser.add_argument("--base-d22ap", default=None)
    known, _unknown = parser.parse_known_args()
    tool = Path(__file__).resolve().parent / "mkadt.py"
    command = [sys.executable, str(tool), known.output, "--device", "nabu",
               "--dram-size", known.dram_size]
    if known.owned_memory_size is not None:
        command += ["--owned-memory-size", str(known.owned_memory_size)]
    if known.base_d22ap is not None:
        import os
        env = dict(os.environ)
        env["UNIXNU_D22AP_ADT"] = known.base_d22ap
        subprocess.run(command, check=True, env=env)
        return
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()