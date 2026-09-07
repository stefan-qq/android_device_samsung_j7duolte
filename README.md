# Samsung Galaxy J7 Duo SM-J720F (j7duolte) — Unofficial TWRP 3.3.0-0

Unofficial TWRP recovery for the Samsung Galaxy J7 Duo **SM-J720F**
(`j7duolte`).

Hardware qualification was performed on:

- Model: SM-J720F
- Region / CSC: XSG / UAE
- Stock base: Android 10 CUL1
- AP: J720FDDS7CUL1
- CSC: J720FOJM7CUF1
- Bootloader binary: 7

This release is **not an official TeamWin build**.

No support claim is made for SM-J720G or other J7 Duo variants.

## Qualified release

Release tag:

`j7duolte-twrp-3.3.0-0-unofficial-r1`

Exact functional device-tree commit:

`86cce8693b77cf79850a3e97d081dbdf8bc63936`

Exact builder commit:

`4e2f5051f72a2feeecdc49a634a25484fc1063a9`

GitHub Actions run:

`34086555239`

Exact release artifacts:

```text
recovery.img
SHA256: deaba0394c093f2a628ac54a0f6f05792a337c9a69c831ecc12b2112eb97b199

recovery.tar
SHA256: 0f9b616499cfbf495f4c9b3dae83faf21be1f91879d1122cdca2416f237977d8

Actions artifact ZIP
SHA256: fb57de09b701b91732dff151e28716e7d827ec9990ddd6adab8a1868638ba4d3
```

The final `recovery.img` was also flashed over pristine CUL1 stock and
read back from the live RECOVERY partition. The image-sized readback
matched the release image byte-for-byte.

## Hardware-qualified recovery functionality

The exact release candidate passed:

- GUI, framebuffer and touch
- root recovery ADB
- physical USB reconnect
- MTP enumeration of Internal Storage and microSD
- MTP file-transfer checksum roundtrip with ADB simultaneously available
- microSD read/write
- normal ZIP installation
- ADB sideload
- sideload cancellation and normal ADB return
- Boot backup and restore
- byte-for-byte Boot restore verification
- raw Boot image flashing
- System Image flashing
- immediate byte-for-byte System Image readback verification
- reboot to Recovery
- reboot to Samsung Download Mode
- Power Off
- stock Android boot after a read-only TWRP visit

## Installation on stock Samsung firmware

On Linux, the qualified recovery-flash method is:

```sh
sudo heimdall flash --RECOVERY recovery.img --no-reboot
```

**Important:** after Heimdall finishes, boot directly into recovery with
the hardware keys before allowing Android to start.

Samsung stock Android can automatically restore the Samsung stock recovery
after Android boots. This behavior was reconfirmed during the final CUL1
release qualification.

## Stock Android 10 encrypted /data

CUL1 stock Android uses Samsung legacy encrypted userdata that this TWRP
3.3 recovery does not decrypt.

On freshly restored stock firmware, `/data` may therefore appear as
0 MB or be unmountable in recovery.

`Format Data` removes the stock encryption and creates usable plain ext4
userdata, but it **erases all userdata**.

Do not interpret the stock-encrypted 0 MB condition as a recovery defect.

## Modern Android / GSI userdata limitation

This legacy TWRP 3.3 recovery is not designed for complete file-level
backup and restore of modern Android 13-era userdata policy layouts.

Modern GSIs may produce permission-denied messages while TWRP scans some
`/data` directories.

Do not rely on complete file-level Data backup/restore for modern Android
GSIs.

## Modern storage.xml handling

Modern Android versions may store `/data/system/storage.xml` as binary
Android Binary XML (ABX).

TWRP 3.3 does not implement an ABX metadata parser.

This build contains a narrow compatibility guard that detects unsupported
non-text `storage.xml`, skips only the legacy text-XML metadata parse, and
continues the existing adopted-storage block-device probing.

It does **not** claim ABX metadata support.

## Recovery kernel provenance

The recovery uses the CUL1 stock-derived kernel and device tree with two
audited recovery-only binary changes:

- adbd credential-preservation patch
- MMS438 automatic boot self-test suppression

The recovery does not contain Magisk.

The separate GSI SYSTEM no-verity Boot modification used for modern GSI
booting is **not required to install or use this TWRP recovery**.

## Partition safety

Do not repartition the device for recovery installation.

Do not modify or format EFS or CPEFS.

This project is unofficial and is not affiliated with TeamWin.
