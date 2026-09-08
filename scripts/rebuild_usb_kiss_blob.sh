#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
clang --target=arm-none-eabi -mcpu=cortex-m4 -mthumb -c "$ROOT/src/usb_kiss_uart_tx.S" -o "$TMP/usb.o"
cat > "$TMP/link.ld" <<'EOF'
SECTIONS { . = 0x08043058; .text : { *(.text.usbkiss) *(.text*) } }
EOF
ld.lld -T "$TMP/link.ld" --entry=usb_kiss_rx_byte "$TMP/usb.o" -o "$TMP/usb.elf" >/dev/null
llvm-objcopy -O binary --only-section=.text "$TMP/usb.elf" "$TMP/usb.bin"
python3 - "$ROOT/patches/usb_kiss_tx.json" "$TMP/usb.bin" "$TMP/usb.elf" <<'PY'
import json,re,subprocess,sys
from pathlib import Path
spec=json.loads(Path(sys.argv[1]).read_text())
blob=Path(sys.argv[2]).read_bytes()
code=next(p for p in spec['patches'] if p['address'].lower()=='0x08043058')
if blob != bytes.fromhex(code['replace']):
    raise SystemExit(f'ERROR: assembly blob mismatch: compiled={len(blob)} expected={len(bytes.fromhex(code["replace"]))}')
if len(blob) > 500:
    raise SystemExit(f'ERROR: code cave overflow: {len(blob)} > 500')

def bw(addr,target):
    off=target-(addr+4); val=off & ((1<<25)-1)
    s=(val>>24)&1; i1=(val>>23)&1; i2=(val>>22)&1
    imm10=(val>>12)&0x3ff; imm11=(val>>1)&0x7ff
    j1=(~(i1^s))&1; j2=(~(i2^s))&1
    h1=0xF000|(s<<10)|imm10; h2=0x9000|(j1<<13)|(j2<<11)|imm11
    return h1.to_bytes(2,'little')+h2.to_bytes(2,'little')

uart=next(p for p in spec['patches'] if p['address'].lower()=='0x08025686')
main=next(p for p in spec['patches'] if p['address'].lower()=='0x0800a464')
if bytes.fromhex(uart['replace']) != bw(0x08025686,0x08043058):
    raise SystemExit('ERROR: UART4 hook encoding mismatch')
symtab=subprocess.check_output(['readelf','-sW',sys.argv[3]],text=True)
m=re.search(r'([0-9a-fA-F]{8})\s+\d+\s+FUNC\s+GLOBAL\s+DEFAULT\s+\d+\s+usb_kiss_dispatch_gate',symtab)
if not m:
    raise SystemExit('ERROR: usb_kiss_dispatch_gate symbol missing')
dispatch=(int(m.group(1),16) & ~1)
if bytes.fromhex(main['replace']) != bw(0x0800A464,dispatch):
    raise SystemExit(f'ERROR: main-loop hook encoding mismatch target=0x{dispatch:08X}')
print(f'USB_KISS_ASSEMBLY_MATCH=PASS bytes={len(blob)}')
print('USB_KISS_UART_HOOK=PASS')
print(f'USB_KISS_MAIN_DISPATCH_HOOK=PASS target=0x{dispatch:08X}')
PY
