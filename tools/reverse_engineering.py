#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from btf import extract_raw

BASE = 0x08003000


def load(path: Path) -> bytes:
    data = path.read_bytes()
    if len(data) >= 0x800 and data[0x400:0x410] == bytes.fromhex("5742F67A9219132F45E5108D9C58AA1C"):
        return extract_raw(data)
    return data


def changed_runs(left: bytes, right: bytes):
    if len(left) != len(right):
        raise SystemExit(f"ERROR: image sizes differ: {len(left)} != {len(right)}")
    changed = [i for i, (a, b) in enumerate(zip(left, right)) if a != b]
    runs = []
    for offset in changed:
        if not runs or offset != runs[-1][1] + 1:
            runs.append([offset, offset])
        else:
            runs[-1][1] = offset
    return changed, runs


def main() -> None:
    parser = argparse.ArgumentParser(description="Binary/BTF reverse-engineering helper")
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()

    left = load(args.left)
    right = load(args.right)
    changed, runs = changed_runs(left, right)
    print(f"CHANGED_BYTES={len(changed)}")
    for start, end in runs:
        print(
            f"0x{BASE + start:08X}..0x{BASE + end:08X} "
            f"len={end - start + 1} "
            f"old={left[start:end + 1].hex()} new={right[start:end + 1].hex()}"
        )


if __name__ == "__main__":
    main()
