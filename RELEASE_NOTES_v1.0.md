# RT-950 PRO v1.0

Hardware-validated release based on OEM v0.29.

## Validated functionality

- BLE KISS RX/TX
- USB KISS RX/TX
- Host-originated TX echo suppression
- Reporting App behavior preserved
- Hardened USB KISS TX parser/guard
- Oversize and malformed USB KISS frames recover without entering RF TX
- Known 180/184-byte incident vectors are blocked before PTT
- No PTT freeze in the TEST05 hardware validation gate

## USB KISS TX safety guard

The final TEST05 guard is derived from OEM binary analysis rather than a guessed scalar packet limit:

- raw AX.25: maximum 182 bytes
- digipeaters: maximum 6
- APRS information field: maximum 127 bytes

Frames outside that envelope are dropped and the parser resynchronizes.

## Reproducibility

The repository rebuilds the release deterministically from `oem/OEM_v0.29.BTF`. CI runs the complete TEST05 static gate before publishing the release.
