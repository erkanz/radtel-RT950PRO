#!/usr/bin/env python3
from __future__ import annotations

FEND=0xC0; FESC=0xDB; TFEND=0xDC; TFESC=0xDD
MAX_AX25=182
MAX_SAFE_DIGIS=6
MAX_INFO=127
HEADER_PACK_LEN_OFFSET=64


def fcs(frame: bytes) -> int:
    crc=0xFFFF
    for v in frame:
        crc ^= v
        for _ in range(8):
            crc=((crc>>1)^0x8408) if crc&1 else (crc>>1)
            crc &= 0xFFFF
    return (~crc)&0xFFFF


def encode_kiss(ax: bytes) -> bytes:
    out=bytearray([FEND,0])
    for b in ax:
        if b==FEND: out += bytes([FESC,TFEND])
        elif b==FESC: out += bytes([FESC,TFESC])
        else: out.append(b)
    out.append(FEND)
    return bytes(out)


def tx_shape_safe(buf: bytes) -> bool:
    if len(buf) < 16:
        return False
    if buf[6] & 0x01:
        return False
    final_ssid=None
    for ssid_offset in range(13, 56, 7):
        if ssid_offset >= len(buf):
            return False
        if buf[ssid_offset] & 0x01:
            final_ssid=ssid_offset
            break
    if final_ssid is None:
        return False
    info_start=final_ssid+3
    if len(buf) < info_start:
        return False
    if len(buf)-info_start > MAX_INFO:
        return False
    return True


def model(stream: bytes, queue_busy: bool=False):
    state=0; buf=bytearray(); crc=0xFFFF; staging=None
    for b in stream:
        if state>=5:
            continue
        if state==0:
            if b==FEND:
                if queue_busy: state=4
                else: state=1;buf.clear();crc=0xFFFF
            continue
        if state==1:
            if b==FEND:
                if queue_busy: state=4
                else: state=1;buf.clear();crc=0xFFFF
            elif b==0: state=2
            else: state=4
            continue
        if state==4:
            if b==FEND:
                if queue_busy: state=4
                else: state=1;buf.clear();crc=0xFFFF
            continue
        if state==3:
            if b==FEND:
                if queue_busy: state=4
                else: state=1;buf.clear();crc=0xFFFF
                continue
            if b==TFEND: b=FEND
            elif b==TFESC: b=FESC
            else: state=4;continue
            state=2
        elif state==2:
            if b==FEND:
                if tx_shape_safe(bytes(buf)) and not queue_busy:
                    c=(~crc)&0xFFFF
                    staging=b'RTX1'+bytes(buf)+bytes([c&0xff,c>>8])
                    state=5
                else:
                    state=4 if queue_busy else 1
                    if not queue_busy:
                        buf.clear();crc=0xFFFF
                continue
            if b==FESC:
                state=3;continue
        if len(buf)>=MAX_AX25:
            state=4;continue
        buf.append(b)
        crc ^= b
        for _ in range(8):
            crc=((crc>>1)^0x8408) if crc&1 else crc>>1
            crc &=0xFFFF
    return staging if state==5 else None


def addr(call: str, ssid: int=0, last: bool=False) -> bytes:
    call=call.upper().ljust(6)[:6]
    out=bytearray((ord(c)<<1)&0xff for c in call)
    out.append(0x60 | ((ssid&0x0f)<<1) | (1 if last else 0))
    return bytes(out)


def make_ax(total_len: int, digis: int=0, fill: bytes=b'B') -> bytes:
    assert 0 <= digis <= 7
    addresses=[addr('APRS',0,False), addr('TEST',1,digis==0)]
    for i in range(digis):
        addresses.append(addr(f'WIDE{i+1}',i%8,last=(i==digis-1)))
    header=b''.join(addresses)+bytes([0x03,0xF0])
    info_len=total_len-len(header)
    assert info_len >= 1
    return header+b'>'+fill*(info_len-1)


captured=bytes.fromhex('C0 00 82 A0 82 A8 70 62 E2 96 8A 64 84 A6 88 6E AE 92 88 8A 62 40 62 AE 92 88 8A 64 40 63 03 F0 21 33 34 31 32 2E 37 33 4E 2F 31 30 38 34 39 2E 3A 30 45 26 2F 41 3D 30 30 30 30 30 30 41 50 52 53 43 4E 20 57 49 46 49 20 34 2E 33 30 56 C0')
ax76=captured[2:-1]
expected76=b'RTX1'+ax76+bytes([fcs(ax76)&0xff,fcs(ax76)>>8])
assert len(ax76)==76
assert model(captured)==expected76
assert expected76[-2:]==bytes.fromhex('11 A9')

ax_escape=make_ax(40,digis=0,fill=bytes([FEND]))
assert model(encode_kiss(ax_escape))==b'RTX1'+ax_escape+bytes([fcs(ax_escape)&0xff,fcs(ax_escape)>>8])
assert model(bytes([FEND,0x01])+b'X'*20+bytes([FEND])) is None
assert model(bytes([FEND,0])+b'A'*15+bytes([FEND])) is None
assert model(captured,queue_busy=True) is None

ax135=make_ax(135,digis=0,fill=b'A')
assert len(ax135)-16 == 119
assert tx_shape_safe(ax135)
assert model(encode_kiss(ax135)) is not None

ax143=make_ax(143,digis=0,fill=b'I')
ax144=make_ax(144,digis=0,fill=b'J')
assert len(ax143)-16 == 127 and tx_shape_safe(ax143)
assert model(encode_kiss(ax143)) is not None
assert len(ax144)-16 == 128 and not tx_shape_safe(ax144)
assert model(encode_kiss(ax144)) is None

ax182=make_ax(182,digis=MAX_SAFE_DIGIS,fill=b'B')
assert len(ax182)==182 and tx_shape_safe(ax182)
assert len(ax182)-58 == 124
assert 1 + len(ax182) + 2 + 1 == 186
assert model(encode_kiss(ax182)) is not None

ax183=make_ax(183,digis=MAX_SAFE_DIGIS,fill=b'C')
assert model(encode_kiss(ax183)) is None

ax59_6d=make_ax(59,digis=6,fill=b'S')
assert (ax59_6d[55] & 1) == 1
assert tx_shape_safe(ax59_6d)
assert model(encode_kiss(ax59_6d)) is not None

address_len_7=(2+7)*7
assert address_len_7 == 63
assert address_len_7+1 == HEADER_PACK_LEN_OFFSET
assert 0xF0 == 240
ax66_7d=make_ax(66,digis=7,fill=b'X')
assert (ax66_7d[62] & 1) == 1
assert not tx_shape_safe(ax66_7d)
assert model(encode_kiss(ax66_7d)) is None

ax180=make_ax(180,digis=7,fill=b'A')
ax184=make_ax(184,digis=7,fill=b'E')
ax185=make_ax(185,digis=7,fill=b'F')
ax193=make_ax(193,digis=7,fill=b'N')
assert model(encode_kiss(ax180)) is None
assert model(encode_kiss(ax184)) is None
assert model(encode_kiss(ax185)) is None
assert model(encode_kiss(ax193)) is None

malformed_dest=bytearray(make_ax(40,digis=0,fill=b'M')); malformed_dest[6] |= 1
assert model(encode_kiss(bytes(malformed_dest))) is None
malformed_no_end=bytearray(make_ax(59,digis=6,fill=b'M'))
for off in range(13,56,7): malformed_no_end[off] &= 0xFE
assert model(encode_kiss(bytes(malformed_no_end))) is None

invalid_escape=bytes([FEND,0])+make_ax(20,digis=0,fill=b'I')[:16]+bytes([FESC,0x00,FEND])
assert model(invalid_escape+captured)==expected76
assert model(encode_kiss(ax183)+captured)==expected76
assert model(encode_kiss(ax180)+captured)==expected76
assert model(encode_kiss(ax144)+captured)==expected76

print('PARSER_MODEL_TESTS=PASS')
print('CAPTURED_76_AX25=PASS')
print('TEST05_135_AX25=PASS')
print('TEST05_HARD_MAX_AX25=182')
print('TEST05_182_6DIGI_BOUNDARY=PASS')
print('TEST05_183_BOUNDARY_PLUS_1_DROP=PASS')
print('TEST05_INFO_143_0DIGI_BOUNDARY=PASS')
print('TEST05_INFO_144_0DIGI_DROP=PASS')
print('TEST05_180_INCIDENT_7DIGI_DROP=PASS')
print('TEST05_184_INCIDENT_DROP=PASS')
print('TEST05_185_DROP=PASS')
print('TEST05_193_INCIDENT_DROP=PASS')
print('TEST05_7DIGI_66_STRUCTURAL_DROP=PASS')
print('TEST05_MALFORMED_RECOVERY=PASS')
print('TEST05_QUEUE_BUSY=PASS')
print('OEM_HEADER_PACK_LENGTH_OFFSET=64')
print('OEM_INFO_MAX=127')
print('MAX_SAFE_DIGIS=6')
