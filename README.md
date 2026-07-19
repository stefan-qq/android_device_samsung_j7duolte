# Samsung Galaxy J7 Duo (SM-J720F) — TWRP 3.3 bring-up

This device tree preserves the only proven UI/touch architecture: the Android
7.1 donor-era TWRP 3.3 userspace with the exact J720F Android 10 stock kernel
and DT.

## RC1 verified on hardware

- UI, brightness and touch work.
- FAT32 microSD is detected, mounted and writable.
- EFS and CPEFS are exposed as raw `dd` backups.
- MTP noise and the `uevent not root` error are gone.
- Existing stock-encrypted `/data` is not decryptable.

## RC2 scope

RC2 keeps every verified RC1 component and changes only:

- ConfigFS mount path from `/sys/kernel/config` to Android 7.1's `/config`;
- ADB FunctionFS bind ordering to wait for `sys.usb.ffs.ready=1`;
- removal of the legacy `android_usb` enable/restart trigger;
- `/etc/fstab` as a symlink to writable `/tmp/fstab`;
- one offline `J720F_RC2_USB_REPORT.txt` written to a mounted microSD;
- read-only backup visibility for the 1 MB `misc` partition, so the persistent
  recovery-boot command can be inspected without clearing it blindly.

Do not claim Android 10 userdata decryption. Do not wipe or restore EFS/CPEFS
while validating recovery bring-up.
