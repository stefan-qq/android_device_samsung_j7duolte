# LineageOS 20 GSI testing on SM-J720F

These results describe one tested Android setup on the Galaxy J7 Duo SM-J720F (`j7duolte`). They are not a claim of complete GSI compatibility or official LineageOS support.

| Component | Tested configuration |
| --- | --- |
| GSI | `lineage-20.0-20251021-UNOFFICIAL-arm64_bvN-vndklite.img` |
| Android | 13 / LineageOS 20 |
| Stock base/vendor | XSG/UAE Android 10, AP `J720FDDS7CUL1`, CSC `J720FOJM7CUF1`, binary 7 |
| Recovery | TWRP 3.3.0-0 unofficial release r1 |
| Android BOOT | Separately modified stock BOOT with legacy dm-verity verification disabled for SYSTEM only |

## Recovery and boot verification

The GSI was flashed using TWRP's **System Image** target. An immediate byte-for-byte SYSTEM readback matched the source image and its SHA256, and the GSI booted successfully with the separate BOOT modification.

The BOOT modification is specific to this GSI setup. It is not needed to install or use TWRP, and the recovery does not disable dm-verity by itself. The recovery release contains no modified Android BOOT image.

The separate BOOT image was also patched with Magisk 31.0 and booted with working root. Magisk is optional, is not bundled and is not required for TWRP.

## Android results

Proven working functions include boot/reboot/idle, display/touch, brightness, rotation/vibration, Wi-Fi 2.4 GHz, LTE/mobile data, SIM/SMS, GPS, cameras, speaker media, microphone recording, wired headphones, microSD, charging and ordinary ADB.

Bluetooth media playback through Sony WH-CH720N headphones was verified after reboot with the separate Magisk module `j720f_bt_hybrid` enabled. The module overlays the TrebleDroid `sysbta` audio HAL under the legacy `a2dp` name required by the vendor HIDL audio 2.0 interface. It is a workaround for this Android setup, is not included in TWRP and does not establish Bluetooth call-audio support.

Remaining limitations in this setup:

- Cellular calls connect, but received voice and microphone transmission do not work. Stock Samsung call audio passed hardware testing.
- Android MTP/PTP file transfer remains unresolved. Ordinary ADB works; MTP was separately verified in TWRP.
- Fingerprint and Android device credentials are not a usable baseline because of the credential incompatibility below.

## Android device credentials

Setting an Android device PIN, pattern, password or fingerprint caused a legacy Samsung Keymaster / Android 13 SyntheticPassword incompatibility on this GSI. This is an Android/vendor compatibility issue, not a TWRP bug.

The tested GSI was stable after Format Data with no Android device credential configured. Use swipe unlock for that tested baseline. Format Data erases userdata. A SIM PIN is separate and unrelated to this issue.

## Userdata and partition limits

Stock CUL1 Samsung C5 full-disk encryption cannot be decrypted by this recovery. That is separate from the modern Android userdata limitation: Android 13 SELinux/MCS policy state can prevent this old TWRP from accessing some `/data` directories during file-level backup. Permission-denied messages alone do not establish filesystem corruption, and complete Android 13 file-level Data backup/restore is not supported.

Binary ABX `/data/system/storage.xml` is skipped safely rather than parsed as legacy text XML. This prevents the unsupported metadata parse from hanging; it does not provide full ABX adopted-storage support.

Keep the stock vendor intact. A previous read/write Vendor mount in TWRP was followed by a boot failure; restoring stock Vendor alone restored boot while preserving userdata. Do not treat Vendor read/write access as a routine GSI troubleshooting step. Leave the partition layout and device-specific radio/modem persistent partitions unchanged.

Use ordinary ADB and normal `su` for Android root access. Rooted debugging with `adb root` previously disrupted USB data functions on this setup. Recovery's own root ADB is a separate, tested function.
