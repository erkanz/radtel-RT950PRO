# RT-950 PRO v1.0

BLE KISS support has been added and is working reliably.

- BLE KISS RX: Working
- BLE KISS TX: Working
- USB KISS RX: Working
- USB KISS TX: In progress

Build from the OEM v0.29 firmware:

```bash
python3 tools/fetch_oem_v029.py
python3 scripts/build_v1.py oem/OEM_v0.29.BTF
```
