#!/usr/bin/env python3
from __future__ import annotations
import argparse
import stat
import zipfile
from pathlib import Path

ROOT_NAME = "RT950_V1.0_USB_KISS_TX_TEST05_FULL_SOURCE"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
EXCLUDE_NAMES = {"__pycache__", ".git"}

def iter_files(root: Path):
    for p in sorted(root.rglob('*'), key=lambda x: x.as_posix()):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_NAMES for part in p.parts):
            continue
        if p.suffix == '.pyc':
            continue
        if p.name == f"{ROOT_NAME}.zip":
            continue
        yield p

def write_zip(root: Path, out: Path):
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in iter_files(root):
            rel = p.relative_to(root).as_posix()
            zi = zipfile.ZipInfo(f"{ROOT_NAME}/{rel}", FIXED_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3
            mode = 0o755 if (p.stat().st_mode & stat.S_IXUSR) else 0o644
            zi.external_attr = (mode & 0xFFFF) << 16
            zi.flag_bits = 0
            zf.writestr(zi, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('output', nargs='?', default=f"../{ROOT_NAME}.zip")
    ns = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = Path(ns.output).resolve()
    write_zip(root, out)
    print(out)

if __name__ == '__main__':
    main()
