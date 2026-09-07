#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

BLOCK = 0x400
ENC_START = 0x800
KEY_OFFSET = 0x400
V029_KEY = bytes.fromhex("5742F67A9219132F45E5108D9C58AA1C")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rol8(value: int) -> int:
    return ((value << 1) | (value >> 7)) & 0xFF


def ror8(value: int) -> int:
    return ((value >> 1) | (value << 7)) & 0xFF


def expand_key(key: bytes) -> bytes:
    blocks = [bytes(key)]
    for _ in range(7):
        previous = blocks[-1]
        blocks.append(bytes(rol8(previous[i]) if i < 8 else ror8(previous[i]) for i in range(16)))
    return b"".join(blocks)


def crypt(data: bytes, key: bytes) -> bytes:
    expanded = expand_key(key)
    out = bytearray(data)
    for i in range(ENC_START, len(out)):
        value = out[i]
        if value in (0x00, 0xFF):
            continue
        changed = value ^ expanded[i % len(expanded)]
        if changed in (0x00, 0xFF):
            continue
        out[i] = changed
    return bytes(out)


def extract_raw(btf: bytes) -> bytes:
    if len(btf) < ENC_START:
        raise ValueError("BTF image is too small")
    key = btf[KEY_OFFSET:KEY_OFFSET + 16]
    if key != V029_KEY:
        raise ValueError("Unexpected BTF key")
    decrypted = crypt(btf, key)
    return decrypted[:BLOCK] + decrypted[ENC_START:]


def make_key_block() -> bytes:
    expanded = expand_key(V029_KEY)
    block = bytearray(BLOCK)
    block[:16] = V029_KEY
    block[16:16 + len(expanded)] = expanded
    return bytes(block)


def build_btf(raw: bytes) -> bytes:
    payload = raw[:BLOCK] + make_key_block() + raw[BLOCK:]
    result = crypt(payload, V029_KEY)
    if extract_raw(result) != raw:
        raise ValueError("BTF round-trip verification failed")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="RT-950 PRO V0.29 BTF extract/build tool")
    sub = parser.add_subparsers(dest="command", required=True)

    extract = sub.add_parser("extract")
    extract.add_argument("input", type=Path)
    extract.add_argument("output", type=Path)

    build = sub.add_parser("build")
    build.add_argument("input", type=Path)
    build.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "extract":
        raw = extract_raw(args.input.read_bytes())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
        print(f"RAW_SHA256={sha256(raw)}")
    else:
        raw = args.input.read_bytes()
        btf = build_btf(raw)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(btf)
        print(f"BTF_SHA256={sha256(btf)}")
        print("ROUNDTRIP=PASS")


if __name__ == "__main__":
    main()
