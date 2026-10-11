# TWRP 3.3.0-0 Unofficial for Samsung Galaxy J7 Duo SM-J720F (j7duolte)

Unofficial recovery for **SM-J720F only**. Tested on XSG/UAE Android 10 CUL1: AP `J720FDDS7CUL1`, CSC `J720FOJM7CUF1`, bootloader binary 7. SM-J720G and other variants are unsupported. This is not official Team Win support.

Flashing modifies your device. You are responsible for what you flash; neither the maintainer nor Team Win is responsible for bricked devices, lost data, damaged partitions, warranty issues or other consequences. Back up your files and know how to restore stock firmware first.

## Installation

On Fedora, install Heimdall with `sudo dnf install heimdall`. Verify the image checksum, enter Download Mode and flash only RECOVERY:

```sh
sudo heimdall flash --RECOVERY recovery.img --no-reboot
```

**Immediately boot directly into TWRP before Android starts. Stock Samsung firmware can restore stock recovery automatically.** See the [installation guide](https://github.com/stefan-qq/android_device_samsung_j7duolte/blob/twrp-3.3/README.md#installation) for hardware key steps. No repartitioning is needed; leave PIT, EFS and CPEFS untouched.

## Tested functions and limits

UI/touch, brightness, recovery ADB, USB reconnect, microSD, checksum-verified MTP alongside ADB, ZIP installation, sideload/cancellation, exact Boot backup/restore, raw Boot and System Image flashing, and recovery/download reboot passed testing. The live installed recovery matched the released image byte-for-byte.

Stock CUL1 uses Samsung legacy C5 full-disk encryption, which this recovery cannot decrypt. Encrypted `/data` may be unavailable or show 0 MB. **Format Data permanently erases userdata** and creates plain ext4.

Android 13 GSI file-level Data backup/restore is incomplete: SELinux/MCS policy state can cause permission-denied messages, which do not by themselves indicate corruption. Unsupported binary ABX `storage.xml` is skipped safely; full ABX adopted-storage support is not provided. Power off may restart the device while USB supplies power.

A LineageOS 20 Android 13 `arm64 bvN-vndklite` GSI was flashed to SYSTEM, verified by immediate byte-for-byte readback and source SHA256, and booted with a **separate** stock BOOT modification disabling legacy SYSTEM dm-verity. That modification is not required for TWRP; TWRP does not bypass dm-verity itself. Magisk is optional, is not bundled and is not required. See [GSI results and credential limitations](https://github.com/stefan-qq/android_device_samsung_j7duolte/blob/twrp-3.3/docs/gsi-testing.md).

## Checksums and source

`recovery.img` is the raw Heimdall image; `recovery.tar` contains the same image for Odin. SHA256:

```text
deaba0394c093f2a628ac54a0f6f05792a337c9a69c831ecc12b2112eb97b199  recovery.img
0f9b616499cfbf495f4c9b3dae83faf21be1f91879d1122cdca2416f237977d8  recovery.tar
fb57de09b701b91732dff151e28716e7d827ec9990ddd6adab8a1868638ba4d3  j7duolte-twrp-3.3.0-0-unofficial-r1-build-artifact.zip
```

Release tag in both repositories: `j7duolte-twrp-3.3.0-0-unofficial-r1`.

- [Device-tree functional source: 86cce8693b77cf79850a3e97d081dbdf8bc63936](https://github.com/stefan-qq/android_device_samsung_j7duolte/commit/86cce8693b77cf79850a3e97d081dbdf8bc63936)
- [Builder functional source: 4e2f5051f72a2feeecdc49a634a25484fc1063a9](https://github.com/stefan-qq/TWRP-Recovery-Builder-2024/commit/4e2f5051f72a2feeecdc49a634a25484fc1063a9)
- [Detailed upstream pins and build provenance](https://github.com/stefan-qq/TWRP-Recovery-Builder-2024/blob/twrp-3.3/README.md)

The preserved build ZIP and original metadata remain attached to this release. Later documentation or workflow housekeeping does not change its binary identity. This release is the maintained baseline; bug reports, hardware test results and well-scoped pull requests are welcome.
