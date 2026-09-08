# RT-950 PRO v1.0

BLE KISS support has been added and is working reliably.

- BLE KISS RX: Working
- BLE KISS TX: Working
- USB KISS RX: Working
- USB KISS TX: Working

## APRSdroid BLE KISS Support

For BLE KISS operation with APRSdroid, use the BLE-enabled APRSdroid build available here:

**[APRSdroid BLE](https://github.com/erkanz/aprsdroid-ble)**

The standard APRSdroid application does not include BLE KISS support. BLE support was added to this APRSdroid build to provide direct BLE KISS connectivity with compatible TNC devices.

With the Radtel RT-950 Pro, both **USB KISS** and **BLE KISS** have been tested and are working reliably with this APRSdroid build.

Currently tested devices:

- T-TWR
- Radtel RT-950 Pro

## Build

```bash
git clone https://github.com/erkanz/radtel-RT950PRO.git
cd radtel-RT950PRO
python3 scripts/build_v1.py oem/OEM_v0.29.BTF
```
