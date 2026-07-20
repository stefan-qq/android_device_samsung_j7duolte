# Samsung Galaxy J7 Duo (SM-J720F) — TWRP 3.3 bring-up

This tree keeps the proven Android 7.1 TWRP 3.3 UI/touch userspace together
with the exact Android 10 CUL1 kernel and DT.

## Verified on hardware

- UI, framebuffer, brightness and touch work.
- FAT32 microSD mounts read-write and can carry runtime logs.
- EFS and CPEFS are exposed only as raw backups.
- The old generated-fstab and uevent errors are gone.

## Current USB/policy fix

The boot-supplied runtime DT property overrides the recovery image command
line and reports `androidboot.selinux=enforcing`. The builder therefore patches the recovery-only
Android 7.1 init binary to start SELinux non-enforcing before any init actions.
This allows the stock CUL1 ConfigFS/FunctionFS USB sequence to run. The build
also verifies that the device policy is included in `sepolicy.recovery`.

The TWRP fstab no longer advertises the incorrect legacy
`encryptable=footer` flag. Existing stock Android 10 userdata may still require
a format before it can be mounted by this old recovery userspace.

MTP remains disabled until ADB is proven stable. Do not wipe or restore EFS or
CPEFS while validating recovery bring-up.


## USB architecture

The recovery keeps one coherent donor-era Android 7.1 userspace for init, TWRP,
bionic, the property service and adbd. It reuses only the exact CUL1 stock
kernel/DT and Samsung ConfigFS gadget parameters. The experimental Android 10
adbd/linker/library bundle is intentionally not packaged.
