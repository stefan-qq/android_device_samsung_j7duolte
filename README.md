# Samsung Galaxy J7 Duo (SM-J720F / j7duolte) — Unofficial TWRP 3.3

Device tree for an unofficial TWRP 3.3 recovery targeting the Samsung Galaxy
J7 Duo SM-J720F (`j7duolte`), qualified on the Android 10 CUL1 firmware base.

## Hardware-qualified recovery features

- GUI/framebuffer/brightness and touch
- root ADB shell, including physical USB reconnect
- MTP with internal storage and microSD
- normal ZIP installation and ADB sideload
- RTC read/write and stale-clock correction
- Boot/Data backup and restore
- Factory Reset semantics
- reboot to Recovery, Download Mode and Power Off
- stock Android 10 System boot after a read-only TWRP visit

The recovery keeps the exact CUL1 stock kernel and DT, with two narrowly scoped
recovery-only kernel patches: the proven `/sbin/adbd` credential-preservation
instruction and suppression of the delayed MMS438 boot self-test.

## USB architecture

The recovery uses the donor-era Android 7.1 native FunctionFS adbd with the
Samsung stock ConfigFS ordering required by the CUL1 kernel. The parent adbd
remains root in `u:r:adbd:s0`; command children transition to
`u:r:recovery:s0`. A one-shot `j720f.usb.rebind_req` state machine prevents
host-side USB resets from replaying the destructive Samsung rebind sequence.
MTP uses the kernel `mtp.0` function and coexists with the permanent `ffs.adb`
registration.

## Known limitation: stock Android 10 encrypted /data

CUL1 stock Android uses Samsung-specific legacy full-disk encryption metadata
(`0xD0B5B1C5`, version 1.3, `aes-xts-disk`) in the final 16 KiB of USERDATA.
This TWRP build does not decrypt that stock-encrypted layout, so a freshly
stock-encrypted `/data` can appear as 0 MB in recovery.

Plain ext4 `/data` is hardware-proven read/write. Formatting Data in TWRP
removes the stock encryption and makes `/data` and Internal Storage usable, but
**permanently erases existing userdata**.

## Installation note

When flashing TWRP over stock Samsung firmware, boot directly into recovery
before allowing Android to start. Stock Android can restore Samsung recovery on
the next boot. On Linux, the proven flash method is:

```sh
sudo heimdall flash --RECOVERY recovery.img --no-reboot
```

Then use the hardware recovery key combination immediately.

EFS and CPEFS are exposed only as raw backup partitions. Do not format them, and
do not use restore operations on them merely for testing.

This project is unofficial and is not affiliated with TeamWin.
