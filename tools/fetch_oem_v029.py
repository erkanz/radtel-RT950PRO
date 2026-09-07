#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html.parser
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

PAGE_URL = "https://www.radtels.com/pages/software-download"
TARGET_MARKERS = ("RT-950 PRO", "V0.29", "260617")
OEM_BTF_SHA256 = "53226024c9b4a782c85556a120afa5e690c132a85bf4048e59d2d193e5eaf272"
V029_KEY = bytes.fromhex("5742F67A9219132F45E5108D9C58AA1C")


class LinkCollector(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None
        self.text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.href = dict(attrs).get("href")
            self.text = []

    def handle_data(self, data):
        if self.href is not None:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.href is not None:
            text = " ".join("".join(self.text).split())
            self.links.append((text, self.href))
            self.href = None
            self.text = []


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 RT950PRO/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def find_download_url(page: bytes) -> str:
    parser = LinkCollector()
    parser.feed(page.decode("utf-8", errors="replace"))
    matches = []
    for text, href in parser.links:
        if href and all(marker.lower() in text.lower() for marker in TARGET_MARKERS):
            matches.append(urllib.parse.urljoin(PAGE_URL, href))
    if len(matches) != 1:
        raise SystemExit(f"ERROR: expected one official OEM V0.29 download, found {len(matches)}")
    return matches[0]


def extract_archive(download: Path, output_dir: Path) -> None:
    data = download.read_bytes()
    if len(data) >= 0x800 and data[0x400:0x410] == V029_KEY:
        shutil.copy2(download, output_dir / "OEM_v0.29.BTF")
        return
    if data.startswith(b"PK"):
        with zipfile.ZipFile(download) as archive:
            archive.extractall(output_dir)
        return
    if data.startswith(b"Rar!\x1a\x07"):
        unar = shutil.which("unar")
        if unar and subprocess.run([unar, "-f", "-o", str(output_dir), str(download)]).returncode == 0:
            return
        seven_zip = shutil.which("7z")
        if seven_zip and subprocess.run([seven_zip, "x", "-y", f"-o{output_dir}", str(download)]).returncode == 0:
            return
    raise SystemExit("ERROR: unsupported OEM download archive")


def locate_btf(output_dir: Path) -> Path:
    matches = []
    for path in output_dir.rglob("*.BTF"):
        data = path.read_bytes()
        if len(data) >= 0x800 and data[0x400:0x410] == V029_KEY:
            matches.append(path)
    if len(matches) != 1:
        raise SystemExit(f"ERROR: expected one OEM BTF, found {len(matches)}")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch official RT-950 PRO OEM V0.29 firmware")
    parser.add_argument("--output-dir", type=Path, default=Path("oem"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = fetch(find_download_url(fetch(PAGE_URL)))
    download = args.output_dir / "official_download.bin"
    download.write_bytes(payload)
    extract_archive(download, args.output_dir)
    btf = locate_btf(args.output_dir)
    target = args.output_dir / "OEM_v0.29.BTF"
    if btf != target:
        shutil.copy2(btf, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if digest != OEM_BTF_SHA256:
        raise SystemExit(f"ERROR: OEM SHA256 mismatch: {digest}")
    print(f"OEM_BTF_SHA256={digest}")
    print(f"OUTPUT={target}")


if __name__ == "__main__":
    main()
