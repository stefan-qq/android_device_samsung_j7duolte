# Samsung Galaxy J7 Duo (SM-J720F) — TWRP 3.3 bring-up

This tree keeps the proven Android 7.1 TWRP 3.3 userspace together with the
exact Samsung Android 10 CUL1 kernel and device tree used by the phone.

## Verified on hardware

- UI, framebuffer, brightness, terminal and FAT32 microSD work.
- Touch is stable after a brief startup pause.
- `Format Data` creates a valid ext4 USERDATA filesystem and `/data` mounts
  read-write, but the enforcing recovery SELinux domain still cannot enumerate
  or write the `system_data_file` directory. That policy issue is intentionally
  kept separate from this USB experiment.
- EFS and CPEFS are exposed only as raw backup partitions.

## Direct FunctionFS diagnostic

The preceding `su`-policy and `adbd`-domain builds both reached the same state:
FunctionFS exposed only `ep0`, `sys.usb.ffs.ready` remained `0`, the ConfigFS
UDC stayed unbound, and the host never enumerated the phone. This branch does
not make another transport-policy guess.

The builder source-instruments the exact synced Android 7.1 adbd. The daemon
writes each decisive FunctionFS operation and its return value/`errno` directly
to `/tmp/J720F_ADBD_USB_TRACE.txt`, independently of host USB, `/data`, logd, or
recovery-domain access to adbd's `/proc` entry. Native ADB tracing is redirected
to `/tmp/J720F_ADBD_TRACE.txt`. After startup, the recovery automatically copies
both traces and the surrounding gadget/kernel state to:

```text
/external_sd/J720F_DIRECT_USB_TRACE/
```

A manual fallback is included:

```sh
sh /sbin/j720f_collect_direct_usb_trace.sh
```

MTP remains disabled until ADB is proven. This is a diagnostic branch, not a
community release. Do not wipe or restore EFS or CPEFS during bring-up.

## Trace-readable data-access diagnostic

The `twrp-3.3-native-ffs-trace-readable-data` branch fixes the direct-trace
file labels and grants recovery the targeted `system_data_file` and
`media_rw_data_file` access needed after Format Data. It remains a diagnostic
branch until USB, ADB, MTP, backup and restore are verified on hardware.
