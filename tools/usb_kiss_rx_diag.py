#!/usr/bin/env python3
"""RT-950 USB KISS RX diagnostic.

Purpose: compare the exact AX.25 bytes exported by the RT-950 USB KISS path
against the BLE KISS path. This tool never writes to the radio; it is RX-only.

Usage (Windows):
    py -m pip install pyserial
    py tools\usb_kiss_rx_diag.py COM27

Optional:
    py tools\usb_kiss_rx_diag.py COM27 --baud 115200 --count 3

The script prints the KISS command, raw AX.25 hex, decoded TNC2 line, and the
information-field ASCII/hex. It is intentionally byte-oriented so a single-byte
corruption such as ASCII '9' (0x39) becoming ':' (0x3A) is visible directly.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from dataclasses import dataclass
from typing import Iterable, Optional

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - runtime dependency message
    print("ERROR: pyserial is required. Install it with: py -m pip install pyserial")
    raise SystemExit(2)

FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD


@dataclass
class Ax25Decoded:
    destination: str
    source: str
    digipeaters: list[str]
    control: int
    pid: int
    information: bytes

    @property
    def tnc2(self) -> str:
        path = ",".join(self.digipeaters)
        header = f"{self.source}>{self.destination}"
        if path:
            header += "," + path
        return header + ":" + printable(self.information)


class KissStreamDecoder:
    def __init__(self) -> None:
        self.inside = False
        self.escape = False
        self.buffer = bytearray()

    def feed(self, chunk: bytes) -> Iterable[bytes]:
        for byte in chunk:
            if byte == FEND:
                if self.inside and self.buffer:
                    yield bytes(self.buffer)
                self.buffer.clear()
                self.inside = True
                self.escape = False
                continue

            if not self.inside:
                continue

            if self.escape:
                if byte == TFEND:
                    self.buffer.append(FEND)
                elif byte == TFESC:
                    self.buffer.append(FESC)
                else:
                    # Preserve malformed escape data rather than inventing a byte.
                    self.buffer.append(byte)
                self.escape = False
            elif byte == FESC:
                self.escape = True
            else:
                self.buffer.append(byte)


def printable(data: bytes) -> str:
    # Do not decode with replacement characters: show every non-printing byte as
    # \xNN so the output remains an exact diagnostic representation.
    parts: list[str] = []
    for b in data:
        if 0x20 <= b <= 0x7E:
            parts.append(chr(b))
        else:
            parts.append(f"\\x{b:02X}")
    return "".join(parts)


def hexline(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def decode_address(block: bytes, is_digi: bool) -> tuple[str, bool]:
    if len(block) != 7:
        raise ValueError("short address")

    chars = []
    for raw in block[:6]:
        c = raw >> 1
        if c == 0x20:
            continue
        if not (0x30 <= c <= 0x39 or 0x41 <= c <= 0x5A):
            raise ValueError(f"invalid callsign byte 0x{c:02X}")
        chars.append(chr(c))

    if not chars:
        raise ValueError("empty callsign")

    ssid_byte = block[6]
    ssid = (ssid_byte >> 1) & 0x0F
    end = bool(ssid_byte & 0x01)
    repeated = is_digi and bool(ssid_byte & 0x80)
    name = "".join(chars)
    if ssid:
        name += f"-{ssid}"
    if repeated:
        name += "*"
    return name, end


def decode_ax25_ui(payload: bytes) -> Ax25Decoded:
    if len(payload) < 16:
        raise ValueError("AX.25 frame too short")

    addresses: list[str] = []
    offset = 0
    terminated = False
    while offset + 7 <= len(payload) and len(addresses) < 10:
        address, end = decode_address(payload[offset : offset + 7], len(addresses) >= 2)
        addresses.append(address)
        offset += 7
        if end:
            terminated = True
            break

    if not terminated or len(addresses) < 2:
        raise ValueError("AX.25 address chain is incomplete")
    if offset + 2 > len(payload):
        raise ValueError("missing AX.25 control/PID")

    control = payload[offset]
    pid = payload[offset + 1]
    info = payload[offset + 2 :]

    return Ax25Decoded(
        destination=addresses[0],
        source=addresses[1],
        digipeaters=addresses[2:],
        control=control,
        pid=pid,
        information=info,
    )


def position_sanity(info: bytes) -> Optional[str]:
    """Return a concise diagnostic for conventional APRS position fields."""
    if not info:
        return None

    dti = info[0]
    start = None
    if dti in (ord("!"), ord("=")):
        start = 1
    elif dti in (ord("/"), ord("@")) and len(info) >= 8:
        start = 8
    if start is None or len(info) < start + 19:
        return None

    lat = info[start : start + 8]
    lon = info[start + 9 : start + 18]
    lat_text = printable(lat)
    lon_text = printable(lon)

    # Expected fixed layouts: ddmm.hhN/S and dddmm.hhE/W. Spaces are legal as
    # APRS position ambiguity; other punctuation in numeric slots is not.
    lat_numeric = (0, 1, 2, 3, 5, 6)
    lon_numeric = (0, 1, 2, 3, 4, 6, 7)
    invalid: list[str] = []
    for i in lat_numeric:
        b = lat[i]
        if b != 0x20 and not (0x30 <= b <= 0x39):
            invalid.append(f"lat[{i}]=0x{b:02X}('{printable(bytes([b]))}')")
    for i in lon_numeric:
        b = lon[i]
        if b != 0x20 and not (0x30 <= b <= 0x39):
            invalid.append(f"lon[{i}]=0x{b:02X}('{printable(bytes([b]))}')")

    status = "VALID-LAYOUT" if not invalid else "MALFORMED: " + ", ".join(invalid)
    return f"APRS POS: lat={lat_text} lon={lon_text} -> {status}"


def main() -> int:
    parser = argparse.ArgumentParser(description="RT-950 USB KISS RX byte diagnostic")
    parser.add_argument("port", help="Windows COM port, e.g. COM27")
    parser.add_argument("--baud", type=int, default=115200, help="serial baud (default: 115200)")
    parser.add_argument("--count", type=int, default=0, help="stop after N KISS DATA frames (0 = run until Ctrl+C)")
    parser.add_argument("--timeout", type=float, default=0.5, help="serial read timeout seconds")
    args = parser.parse_args()

    print("RT-950 USB KISS RX DIAGNOSTIC")
    print("=============================")
    print(f"Port: {args.port}  baud={args.baud}")
    print("Mode: RX ONLY (no bytes are written to the radio)")
    print("Transmit the AnyTone APRS position beacon now. Ctrl+C to stop.\n")

    decoder = KissStreamDecoder()
    data_frames = 0

    try:
        with serial.Serial(args.port, args.baud, timeout=args.timeout) as ser:
            while True:
                chunk = ser.read(4096)
                if not chunk:
                    continue

                for frame in decoder.feed(chunk):
                    if not frame:
                        continue
                    command_byte = frame[0]
                    port = (command_byte >> 4) & 0x0F
                    command = command_byte & 0x0F
                    payload = frame[1:]

                    now = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
                    print(f"[{now}] KISS port={port} command=0x{command:X} payload={len(payload)} bytes")
                    print("AX25 HEX:", hexline(payload))

                    if command != 0:
                        print("NOTE: non-DATA KISS command\n")
                        continue

                    data_frames += 1
                    try:
                        ax = decode_ax25_ui(payload)
                        print(f"CTRL/PID: 0x{ax.control:02X}/0x{ax.pid:02X}")
                        print("TNC2:", ax.tnc2)
                        print("INFO ASCII:", printable(ax.information))
                        print("INFO HEX:  ", hexline(ax.information))
                        sanity = position_sanity(ax.information)
                        if sanity:
                            print(sanity)
                    except ValueError as exc:
                        print("AX25 DECODE ERROR:", exc)
                    print()

                    if args.count > 0 and data_frames >= args.count:
                        return 0

    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except serial.SerialException as exc:
        print(f"ERROR: could not use {args.port}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
