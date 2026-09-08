#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from btf import build_btf, extract_raw

BASE=0x08003000
TEST04_RAW_SHA='3eb70f73341dd950c03d74b71961bba5d1cb60d61c22d73ecc0c8aae94695c50'
TEST05_RAW_SHA='f8a3f087d61c76191cfaf354cb5e39f1ea4703e12ff679d252ba0e7eb1b3fb08'
TEST05_BTF_SHA='0779e1aaf76e75bcd0d8d2c5435a92d0b92aedc5db09df45bda3c38085d342cb'
COMMON=[ROOT/'patches/ble_kiss.json',ROOT/'patches/echo_suppression.json',ROOT/'patches/reporting_app.json']


def sha(data:bytes)->str: return hashlib.sha256(data).hexdigest()


def apply_specs(raw:bytes, specs:list[Path])->bytes:
    image=bytearray(raw)
    for fn in specs:
        spec=json.loads(fn.read_text())
        for p in spec['patches']:
            a=int(p['address'],16); off=a-BASE
            e=bytes.fromhex(p['expect']); r=bytes.fromhex(p['replace'])
            assert len(e)==len(r),(fn,p['address'],'size')
            got=bytes(image[off:off+len(e)])
            assert got==e,(fn,p['address'],got.hex(),e.hex())
            image[off:off+len(r)]=r
    return bytes(image)


def region(image:bytes,start:int,end:int)->bytes:
    return image[start-BASE:end-BASE+1]


oem_btf=(ROOT/'oem/OEM_v0.29.BTF').read_bytes()
oem_raw=extract_raw(oem_btf)
t04=apply_specs(oem_raw,COMMON+[ROOT/'reference/usb_kiss_tx_TEST04.json'])
t05=apply_specs(oem_raw,COMMON+[ROOT/'patches/usb_kiss_tx.json'])
assert sha(t04)==TEST04_RAW_SHA
assert sha(t05)==TEST05_RAW_SHA
assert sha(build_btf(t05))==TEST05_BTF_SHA
assert extract_raw(build_btf(t05))==t05
print('BTF_ROUND_TRIP=PASS')

changed=[i for i,(a,b) in enumerate(zip(t04,t05)) if a!=b]
def allowed(addr:int)->bool:
    return (0x0800A464 <= addr <= 0x0800A467) or (0x08043058 <= addr <= 0x080431EF)
assert changed and all(allowed(BASE+i) for i in changed)
assert region(t04,0x08025686,0x08025689)==region(t05,0x08025686,0x08025689)
print(f'TEST04_TO_TEST05_CHANGED_BYTES=PASS count={len(changed)}')
print('UART4_HOOK_UNCHANGED_FROM_TEST04=PASS')

protected={
    'RF_TX_ENGINE':(0x08009414,0x0800954F),
    'REPORTING_APP_PATCH':(0x08009648,0x0800966B),
    'ECHO_TX_REPORT_GATE':(0x080097B6,0x080097DF),
    'RTX1_HANDLER':(0x0800BE84,0x0800BECF),
    'USB_RX_FORMATTER':(0x08017454,0x08017555),
    'OEM_AX25_INFO_PARSER_CORE':(0x08009550,0x08009647),
    'OEM_HEADER_PACKER':(0x08029770,0x080297A9),
    'OEM_HDLC_BUILDER':(0x08028B60,0x08028BEF),
    'OEM_BIT_STUFFER':(0x0802A940,0x0802AA13),
}
for name,(start,end) in protected.items():
    assert region(t04,start,end)==region(t05,start,end),(name,hex(start),hex(end))
    print(f'PROTECTED_{name}=PASS 0x{start:08X}..0x{end:08X}')
print('BLE_QUEUE_REGRESSION_STATIC=PASS')
print('USB_RX_PROTECTED=PASS')

with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
    for d in (a,b):
        subprocess.run([sys.executable,str(ROOT/'scripts/build_v1.py'),str(ROOT/'oem/OEM_v0.29.BTF'),'--output-dir',d],check=True,stdout=subprocess.DEVNULL)
    ar=Path(a,'RT950_V029_v1.0_USB_KISS_TX_TEST05.firmware.bin').read_bytes()
    br=Path(b,'RT950_V029_v1.0_USB_KISS_TX_TEST05.firmware.bin').read_bytes()
    ab=Path(a,'RT950_V029_v1.0_USB_KISS_TX_TEST05.BTF').read_bytes()
    bb=Path(b,'RT950_V029_v1.0_USB_KISS_TX_TEST05.BTF').read_bytes()
    assert ar==br==t05 and ab==bb==build_btf(t05)
print('DETERMINISTIC_BUILD=PASS')

subprocess.run([sys.executable,str(ROOT/'tests/test_usb_kiss_tx.py')],check=True)
subprocess.run(['bash',str(ROOT/'scripts/rebuild_usb_kiss_blob.sh')],check=True)
print('STATIC_GATE=PASS')
