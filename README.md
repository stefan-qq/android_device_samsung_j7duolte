# TWRP 3.3.0-0 for Samsung Galaxy J7 Duo SM-J720F

Unofficial TWRP recovery for the Samsung Galaxy J7 Duo SM-J720F (`j7duolte`).

This device tree is intended for the SM-J720F only. It was tested on XSG/UAE Android 10 CUL1 firmware.

## Release

Current release: `j7duolte-twrp-3.3.0-0-unofficial-r1`

Download the release from the GitHub Releases page of this repository.

Release binaries:

```text
recovery.img
SHA256: deaba0394c093f2a628ac54a0f6f05792a337c9a69c831ecc12b2112eb97b199

recovery.tar
SHA256: 0f9b616499cfbf495f4c9b3dae83faf21be1f91879d1122cdca2416f237977d8
```

## Tested device and firmware

| Item | Value |
| --- | --- |
| Model | SM-J720F |
| Device | j7duolte |
| Region / CSC | XSG / UAE |
| Android base | Android 10 |
| AP | J720FDDS7CUL1 |
| CSC | J720FOJM7CUF1 |
| Bootloader binary | 7 |
| Security patch | 2021-12-01 |

No support claim is made for SM-J720G or other J7 Duo variants.

## Installation

Linux with Heimdall:

```sh
sudo heimdall flash --RECOVERY recovery.img --no-reboot
```

After flashing, immediately boot directly into recovery with the hardware key combination.

Do not let Android boot first. Samsung stock firmware can restore the stock recovery after Android starts. This behavior was confirmed during final testing on CUL1.

TWRP installation does not require repartitioning. Do not modify the PIT or partition layout.

## Stock encrypted /data

CUL1 stock firmware uses Samsung legacy full-disk encryption that this TWRP version cannot decrypt.

On fresh stock firmware, `/data` can therefore appear as 0 MB or fail to mount in recovery.

Using `Format Data` removes the stock encryption and creates usable plain ext4 userdata, but it permanently erases userdata.

## Modern Android / GSI notes

Modern Android GSIs can produce permission-denied messages while this legacy TWRP scans parts of `/data`. Complete file-level Data backup and restore should not be assumed for Android 13-era GSIs.

Modern Android can also store `/data/system/storage.xml` as Android Binary XML. TWRP 3.3 does not contain an ABX parser. This build detects unsupported non-text `storage.xml`, skips the legacy metadata parse, and continues the existing adopted-storage block-device probing.

The separate GSI no-verity Boot modification used on this device is not required to install or use TWRP.

Magisk is not included in this recovery.

## Tested recovery functions

The release was tested for:

- GUI, framebuffer, brightness and touch
- root recovery ADB
- physical USB reconnect
- microSD read/write
- MTP transfer with checksum verification
- MTP and ADB at the same time
- normal ZIP installation
- ADB sideload and sideload cancellation
- Boot backup and restore with byte-for-byte verification
- raw Boot image flashing
- System Image flashing with immediate readback verification
- reboot to Recovery
- reboot to Download Mode
- Power Off with USB unplugged
- stock Android boot after a read-only TWRP visit
- final recovery-only flash over pristine CUL1 stock
- live recovery image readback matching the released image

## Recovery kernel

The recovery uses the CUL1 stock-derived kernel and device tree with two recovery-only binary changes used by the tested build:

- adbd credential-preservation patch
- MMS438 automatic boot self-test suppression

## Source and build provenance

The release tag points to the exact device-tree source used for the released binary.

```text
Release tag:
j7duolte-twrp-3.3.0-0-unofficial-r1

Device tree:
86cce8693b77cf79850a3e97d081dbdf8bc63936

Builder:
4e2f5051f72a2feeecdc49a634a25484fc1063a9

TWRP:
b1a7ae9cd98e6ac3377d1fecc1341b9643a4f15b

system/core:
274f5e70d16b80fb6d464aeed3294695fb34fb43

bionic:
cb0033e69dd22cb42f7a2d6d87cb38ba45cca7da
```

The build and provenance tooling is maintained in:

https://github.com/stefan-qq/TWRP-Recovery-Builder-2024

The original GitHub Actions run is no longer retained in the Actions history. The exact build artifact is preserved with the release as:

```text
j7duolte-twrp-3.3.0-0-unofficial-r1-build-artifact.zip
SHA256: fb57de09b701b91732dff151e28716e7d827ec9990ddd6adab8a1868638ba4d3
```

The release tag and binary hashes remain the source of truth for release r1.

## Safety

Do not format, flash or modify EFS or CPEFS for recovery installation or testing.

Do not repartition the device for this recovery.

## Credits

- TeamWin Recovery Project
- OmniROM and Android Open Source Project contributors
- `kinguser981/TWRP-Recovery-Builder-2024` for the upstream GitHub Actions builder project used as the starting point for the build harness

This project is unofficial and is not affiliated with TeamWin.
