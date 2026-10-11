# TWRP 3.3.0-0 Unofficial for Samsung Galaxy J7 Duo SM-J720F (j7duolte)

<p align="center">
  <img src="docs/images/twrp-logo.png" alt="Team Win Recovery Project logo" width="144">
</p>

Unofficial recovery for the **SM-J720F only**, tested on XSG/UAE Android 10 CUL1. This project is not official Team Win support and is not endorsed by Team Win or Samsung.

[Download the maintained release](https://github.com/stefan-qq/android_device_samsung_j7duolte/releases/tag/j7duolte-twrp-3.3.0-0-unofficial-r1) · [Build tooling and provenance](https://github.com/stefan-qq/TWRP-Recovery-Builder-2024)

Flashing custom recovery modifies your device. You are responsible for what you flash; neither the maintainer nor Team Win is responsible for bricked devices, lost data, damaged partitions, warranty issues or other consequences. Make backups and know how to restore stock firmware before proceeding.

## Tested device

| Item | Tested value |
| --- | --- |
| Device | Samsung Galaxy J7 Duo |
| Model / codename | SM-J720F / `j7duolte` |
| Region | XSG / UAE |
| Firmware | Android 10 CUL1 |
| AP | `J720FDDS7CUL1` |
| CSC | `J720FOJM7CUF1` |
| Bootloader binary | 7 |
| Security patch | 2021-12-01 |

SM-J720G and other variants are unsupported. Other firmware and CSC combinations have not been qualified.

## What works

The released image passed hardware testing for:

- Recovery UI, display, brightness and touch.
- Root ADB in recovery and USB reconnect.
- microSD read/write.
- MTP transfers with checksum verification, including simultaneous MTP and ADB.
- ZIP installation, ADB sideload and cancellation, with ADB returning afterward.
- Boot backup/restore with byte-for-byte verification and raw Boot image flashing.
- System Image flashing with immediate byte-for-byte readback verification.
- Reboot to Recovery and Download Mode; power off with USB unplugged.
- Recovery-only installation over pristine CUL1, live image readback matching the release, and stock Android boot after a read-only recovery visit.

## Known limitations

- Stock CUL1 encrypted `/data` cannot be decrypted. See [Stock /data encryption](#stock-data-encryption).
- Complete Android 13 GSI file-level Data backup/restore is not supported. See [GSI testing](#gsi-testing).
- Binary ABX storage metadata is skipped safely; full ABX adopted-storage support is not provided.
- Power off while USB supplies power may restart the device. Unplugged power off passed testing.

EFS and CPEFS contain device-specific radio/modem persistent data. This recovery exposes them for raw backup only. Do not format, wipe, experiment with them or restore random images to them. Do not distribute their backups.

## Installation

**Boot directly into TWRP after flashing RECOVERY, before Android starts. Stock Samsung firmware can restore stock recovery automatically.**

1. Confirm the model is SM-J720F and that the bootloader permits custom binaries. Back up your files and have the correct stock firmware available.
2. Download `recovery.img` from the [release](https://github.com/stefan-qq/android_device_samsung_j7duolte/releases/tag/j7duolte-twrp-3.3.0-0-unofficial-r1) and compare `sha256sum recovery.img` with the checksum below.
3. Install Heimdall on Fedora with `sudo dnf install heimdall`. Power off the phone, hold **Volume Down + Home + Power**, then confirm Download Mode with Volume Up. Connect it to the computer by USB.
4. From the directory containing the image, flash only RECOVERY:

   ```sh
   sudo heimdall flash --RECOVERY recovery.img --no-reboot
   ```

5. After a successful flash, hold **Volume Down + Power** until the screen goes black, then immediately switch to **Volume Up + Home + Power** to enter TWRP. Keep Android from booting first.

Choose **Keep System Read Only** for an initial visit if you intend to keep stock Android unchanged. Formatting Data is a separate, destructive operation, not an installation requirement.

No repartitioning or PIT changes are needed. Leave EFS and CPEFS untouched.

## Stock /data encryption

Stock CUL1 uses Samsung legacy C5 full-disk encryption. This TWRP does not decrypt that format, so stock encrypted `/data` may be unavailable or show 0 MB.

**Wipe > Format Data permanently erases userdata, including internal storage.** It removes the stock encryption and creates usable plain ext4 userdata. Copy anything you need elsewhere before using it.

## GSI testing

This recovery successfully flashed a LineageOS 20 / Android 13 `arm64 bvN-vndklite` GSI to SYSTEM. An immediate byte-for-byte readback matched the source image and its SHA256. The GSI then booted using a separate stock BOOT modification that disables legacy dm-verity verification for SYSTEM only.

**That BOOT modification is a GSI compatibility step. It is not required to install or use TWRP, and TWRP does not bypass dm-verity by itself.** Neither the BOOT modification nor Magisk is bundled in this recovery. Magisk is optional and is not required for TWRP.

Android 13 userdata can carry SELinux/MCS policy state that this TWRP generation does not fully handle during file-level backup. Permission-denied messages for some `/data` directories are a compatibility limitation and do not by themselves indicate filesystem corruption. Complete Android 13 file-level Data backup/restore must not be assumed.

Modern Android may store `/data/system/storage.xml` in binary ABX format. This build skips unsupported binary metadata instead of trying to parse it as legacy text XML and hanging. It does not add an ABX parser or full ABX adopted-storage support.

See [GSI test results](docs/gsi-testing.md) for the tested image, working functions, remaining call-audio/USB issues and the Android device-credential limitation.

## Downloads

Maintained release: [j7duolte-twrp-3.3.0-0-unofficial-r1](https://github.com/stefan-qq/android_device_samsung_j7duolte/releases/tag/j7duolte-twrp-3.3.0-0-unofficial-r1).

- [recovery.img](https://github.com/stefan-qq/android_device_samsung_j7duolte/releases/download/j7duolte-twrp-3.3.0-0-unofficial-r1/recovery.img): raw image for Heimdall.
- [recovery.tar](https://github.com/stefan-qq/android_device_samsung_j7duolte/releases/download/j7duolte-twrp-3.3.0-0-unofficial-r1/recovery.tar): Odin package containing the same image.
- [Preserved build artifact](https://github.com/stefan-qq/android_device_samsung_j7duolte/releases/download/j7duolte-twrp-3.3.0-0-unofficial-r1/j7duolte-twrp-3.3.0-0-unofficial-r1-build-artifact.zip): original output, metadata and audit reports.

SHA256:

```text
deaba0394c093f2a628ac54a0f6f05792a337c9a69c831ecc12b2112eb97b199  recovery.img
0f9b616499cfbf495f4c9b3dae83faf21be1f91879d1122cdca2416f237977d8  recovery.tar
fb57de09b701b91732dff151e28716e7d827ec9990ddd6adab8a1868638ba4d3  j7duolte-twrp-3.3.0-0-unofficial-r1-build-artifact.zip
```

The release also includes [checksums](https://github.com/stefan-qq/android_device_samsung_j7duolte/releases/download/j7duolte-twrp-3.3.0-0-unofficial-r1/SHA256SUMS), [release metadata](https://github.com/stefan-qq/android_device_samsung_j7duolte/releases/download/j7duolte-twrp-3.3.0-0-unofficial-r1/RELEASE-METADATA.txt) and the [hardware qualification report](https://github.com/stefan-qq/android_device_samsung_j7duolte/releases/download/j7duolte-twrp-3.3.0-0-unofficial-r1/QUALIFICATION-SUMMARY.txt).

## Build and source provenance

The release tag is fixed at the functional source commits used for the published binary:

| Repository | Functional release commit |
| --- | --- |
| Device tree | [86cce8693b77cf79850a3e97d081dbdf8bc63936](https://github.com/stefan-qq/android_device_samsung_j7duolte/commit/86cce8693b77cf79850a3e97d081dbdf8bc63936) |
| Builder | [4e2f5051f72a2feeecdc49a634a25484fc1063a9](https://github.com/stefan-qq/TWRP-Recovery-Builder-2024/commit/4e2f5051f72a2feeecdc49a634a25484fc1063a9) |

The maintained branch in both repositories is `twrp-3.3`. Later documentation cleanup does not change the released binary or become its functional source. The builder also has a later workflow-default update; use the release tag and resolved build metadata when inspecting the original build.

The recovery uses the CUL1 stock-derived kernel and device tree with two recovery-only binary changes: ADB credential preservation and suppression of the automatic MMS438 boot self-test. See the [builder README](https://github.com/stefan-qq/TWRP-Recovery-Builder-2024/blob/twrp-3.3/README.md) for upstream source pins, the resolved manifest and audit details. The original Actions run has expired; its exact output ZIP remains attached to the release.

## Credits

- [Team Win Recovery Project](https://twrp.me/) for TWRP.
- [OmniROM](https://github.com/omnirom/android_bootable_recovery) and the [Android Open Source Project](https://source.android.com/) for the legacy recovery source and platform components.
- [Samsung](https://opensource.samsung.com/) for the kernel platform; this release uses stock-derived CUL1 kernel/device-tree binaries.
- [kinguser981](https://github.com/kinguser981/TWRP-Recovery-Builder-2024) for the original builder project.
- [Heimdall](https://git.sr.ht/~grimler/Heimdall) for Linux flashing support.

The TWRP logo is included unchanged from the pinned upstream recovery source. See [artwork attribution and license](docs/images/README.md).

## Contributing and issues

[Bug reports](https://github.com/stefan-qq/android_device_samsung_j7duolte/issues), hardware test results, documentation improvements and well-scoped pull requests are welcome. Include the model, firmware/CSC, recovery checksum, steps to reproduce and relevant logs. For recovery issues, use **Advanced > Copy Log** or `adb pull /tmp/recovery.log`, and remove personal identifiers before posting.

Report Android/GSI compatibility issues separately from recovery failures. A working recovery MTP transfer does not establish that Android's MTP implementation works.

## Project status

The initial port and release development are complete. The project is now in maintenance mode, with the current release as the maintained baseline. No major new feature work is planned; reproducible bug fixes and useful hardware-test reports remain welcome.
