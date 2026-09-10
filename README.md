# ⚠️ **WORK IN PROGRESS**

> [!WARNING]
> ## **This firmware is still under active development and testing.**
>
> **Some features may be incomplete, experimental, or may not work as expected.**
>
> **Use at your own discretion.**

# RT-950 PRO v1.1

BLE KISS support has been added and is working reliably.

- BLE KISS RX: Working
- BLE KISS TX: Working
- USB KISS RX: Working
- USB KISS TX: Working

## Latest tested changes

- APRS SMS receive and transmit support with message IDs.
- Automatic APRS message ACK support, including FT3 CR-terminated message IDs.
- SMS popup remains visible while ACK is transmitted, with improved popup text readability.
- OEM APRS beacon display behavior is preserved.
- Bluetooth programming and BLE KISS now share the BLE receive path without conflict.
- Hardware regression tests pass for Bluetooth programming with TNC OFF/ON, BLE KISS, USB KISS, APRS SMS, auto-ACK, and beacon display.

Current firmware version: **v1.1**.

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

## APRSdroid BLE KISS Support

For BLE KISS operation with APRSdroid, use the BLE-enabled APRSdroid build available here:

**[APRSdroid BLE](https://github.com/erkanz/aprsdroid-ble)**

The standard APRSdroid application does not include BLE KISS support. BLE support was added to this APRSdroid build to provide direct BLE KISS connectivity with compatible TNC devices.

With the Radtel RT-950 Pro, both **USB KISS** and **BLE KISS** have been tested and are working reliably with this APRSdroid build.

Currently tested devices:

- T-TWR Plus
- Radtel RT-950 Pro

## Build

The build entry point is version-independent. Use the same command for future firmware versions:

```bash
git clone https://github.com/erkanz/radtel-RT950PRO.git
cd radtel-RT950PRO
python3 scripts/build.py oem/OEM_v0.29.BTF
```
