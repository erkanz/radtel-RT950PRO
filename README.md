# RT-950 PRO v1.0 — OEM v0.29 + BLE/USB KISS

This repository deterministically rebuilds the **hardware-validated RT-950 PRO v1.0 firmware** directly from **OEM v0.29**.

Final validation date: **2026-09-08**

## Hardware-validated features

- BLE KISS RX: PASS
- BLE KISS TX: PASS
- USB KISS RX: PASS
- USB KISS TX: PASS
- Host-originated TX echo suppression: PASS
- Reporting App behavior preserved
- USB KISS oversize/malformed guard recovery: PASS
- Known 180/184-byte incident vectors: safely DROP / NO PTT
- PTT freeze regression: NOT OBSERVED on TEST05 hardware gate

## USB KISS TX TEST05 safety envelope

TEST05 is the final v1.0 baseline. Binary analysis identified three independent constraints in the unchanged OEM TX path:

1. OEM HDLC builder raw AX.25 ceiling: **182 bytes**.
2. OEM header packer structural limit: **maximum 6 digipeaters**. A 7th digipeater collides with the OEM header-length metadata field.
3. OEM APRS information-field full-fidelity limit: **127 bytes**.

A USB KISS DATA frame reaches the existing RTX1/RF TX path only when all three constraints are satisfied. Otherwise it is dropped and the parser resynchronizes without starting PTT.

For ordinary APRS UI frames the effective raw AX.25 limits are:

| Digipeaters | Max raw AX.25 |
|---:|---:|
| 0 | 143 |
| 1 | 150 |
| 2 | 157 |
| 3 | 164 |
| 4 | 171 |
| 5 | 178 |
| 6 | 182 |
| 7 | DROP |

## Build

```bash
python3 scripts/build_v1.py oem/OEM_v0.29.BTF
python3 tests/run_static_gate.py
```

Expected TEST05 hashes:

```text
0779e1aaf76e75bcd0d8d2c5435a92d0b92aedc5db09df45bda3c38085d342cb  RT950_V029_v1.0_USB_KISS_TX_TEST05.BTF
f8a3f087d61c76191cfaf354cb5e39f1ea4703e12ff679d252ba0e7eb1b3fb08  RT950_V029_v1.0_USB_KISS_TX_TEST05.firmware.bin
```

The GitHub release publishes the same validated binaries under the canonical v1.0 names `RT950_V029_v1.0.BTF` and `RT950_V029_v1.0.firmware.bin`.
