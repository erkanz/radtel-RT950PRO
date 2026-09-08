#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from btf import build_btf, extract_raw  # noqa: E402

BASE = 0x08003000
OEM_BTF_SHA256 = "53226024c9b4a782c85556a120afa5e690c132a85bf4048e59d2d193e5eaf272"
OEM_RAW_SHA256 = "025bc583802a96911836e274cdfdf3ce05d9919bc77451b7f7f1573fb5571907"
FINAL_BTF_SHA256 = "0779e1aaf76e75bcd0d8d2c5435a92d0b92aedc5db09df45bda3c38085d342cb"
FINAL_RAW_SHA256 = "f8a3f087d61c76191cfaf354cb5e39f1ea4703e12ff679d252ba0e7eb1b3fb08"
PATCH_FILES = [
    ROOT / "patches" / "ble_kiss.json",
    ROOT / "patches" / "echo_suppression.json",
    ROOT / "patches" / "reporting_app.json",
    ROOT / "patches" / "usb_kiss_tx.json",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply_patch(image: bytearray, address: int, expect: bytes, replace: bytes, purpose: str) -> None:
    if len(expect) != len(replace):
        raise SystemExit(f"ERROR: patch changes image size: {purpose}")
    offset = address - BASE
    current = bytes(image[offset:offset + len(expect)])
    if current != expect:
        raise SystemExit(
            f"ERROR: patch precondition failed at 0x{address:08X}: {purpose}\n"
            f"got={current.hex()} expected={expect.hex()}"
        )
    image[offset:offset + len(replace)] = replace


def main() -> None:
    parser = argparse.ArgumentParser(description="Build RT-950 PRO USB KISS TX TEST05 from OEM V0.29")
    parser.add_argument("oem_btf", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build")
    args = parser.parse_args()

    oem_btf = args.oem_btf.read_bytes()
    if sha256(oem_btf) != OEM_BTF_SHA256:
        raise SystemExit(f"ERROR: OEM BTF SHA256 mismatch: {sha256(oem_btf)}")
    raw = extract_raw(oem_btf)
    if sha256(raw) != OEM_RAW_SHA256:
        raise SystemExit(f"ERROR: OEM raw SHA256 mismatch: {sha256(raw)}")

    image = bytearray(raw)
    for patch_file in PATCH_FILES:
        spec = json.loads(patch_file.read_text())
        for patch in spec["patches"]:
            apply_patch(
                image,
                int(patch["address"], 16),
                bytes.fromhex(patch["expect"]),
                bytes.fromhex(patch["replace"]),
                patch["purpose"],
            )

    final_raw = bytes(image)
    final_btf = build_btf(final_raw)
    if sha256(final_raw) != FINAL_RAW_SHA256:
        raise SystemExit(f"ERROR: final raw verification failed: {sha256(final_raw)}")
    if sha256(final_btf) != FINAL_BTF_SHA256:
        raise SystemExit(f"ERROR: final BTF verification failed: {sha256(final_btf)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.output_dir / "RT950_V029_v1.0_USB_KISS_TX_TEST05.firmware.bin"
    btf_path = args.output_dir / "RT950_V029_v1.0_USB_KISS_TX_TEST05.BTF"
    raw_path.write_bytes(final_raw)
    btf_path.write_bytes(final_btf)

    print("BUILD=PASS")
    print(f"RAW_SHA256={FINAL_RAW_SHA256}")
    print(f"BTF_SHA256={FINAL_BTF_SHA256}")
    print(f"RAW={raw_path}")
    print(f"BTF={btf_path}")


if __name__ == "__main__":
    main()
