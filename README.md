# Samsung Galaxy J7 Duo (SM-J720F) — TWRP 3.3 bring-up

This tree keeps the proven Android 7.1 TWRP 3.3 userspace together with the
exact Samsung Android 10 CUL1 kernel and device tree used by the phone.

## Verified on hardware

- UI, framebuffer, brightness, terminal and FAT32 microSD work.
- Touch is stable after a brief startup pause.
- `Format Data` creates a valid ext4 USERDATA filesystem. `/data`,
  `/data/media`, internal storage and TWRP settings are now accessible under
  enforcing SELinux.
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

## Forced FunctionFS entry diagnostic

The `twrp-3.3-native-ffs-force-ffs-entry` branch follows the first readable
adbd trace. That trace proved adbd entered its event loop and opened the default
TCP transport on port 5555 without ever calling `usb_init()`. The branch starts
adbd only after an explicit FunctionFS-mounted property is set, instruments the
pre-USB gate in `daemon/main.cpp`, and forces this recovery-only adbd into the
FunctionFS implementation. If the former one-shot gate was the blocker, USB can
enumerate; otherwise the direct trace records the exact `ep0` or descriptor
failure. `/data` access from the prior branch is retained.

## Forced-entry property visibility correction

Hardware trace from the first forced-entry build showed that adbd still chose
TCP fallback because `property_get("j720f.usb.transport")` returned an empty
value even though recovery later displayed the property. The `j720f.` namespace
is labelled `twrp_prop`, and adbd lacked read access to that property area. This
revision adds read-only `get_prop(adbd, twrp_prop)` access and records the exact
SELinux labels and metadata for every FunctionFS path component.

## Root-owned FunctionFS endpoints

The forced-entry trace reached the native FunctionFS open thread and proved the
remaining failure was the first real operation: `open(ep0, O_RDWR)` returned
`EACCES` on every retry. Runtime metadata showed that FunctionFS had created a
mode-0600 `ep0` owned by `shell:shell`, while this recovery intentionally keeps
adbd as UID/GID 0. This revision mounts FunctionFS with `uid=0,gid=0` and keeps
the endpoint ownership rules aligned with the root adbd service.

## Stock-order ConfigFS ADB binding

The root-owned endpoint build completed every adbd FunctionFS operation:
`ep0`, descriptors, strings, `ep1`, `ep2`, transport registration and
`sys.usb.ffs.ready=1`. A later pure-ConfigFS test still failed UDC binding with
`Config c/1 of g1 needs at least one function`, even though the link created in
the ready action remained visible at `configs/c.1/ffs.adb`.

The exact CUL1 Samsung recovery registers `functions/ffs.adb` with
`configs/c.1` before it mounts FunctionFS. This revision follows that kernel-
specific order: create and preserve the configuration link during `fs`, then
mount FunctionFS, start the root adbd, and bind `13600000.dwc3` only after
`sys.usb.ffs.ready=1`. The `none` action no longer removes the link. MTP remains
intentionally disabled until ADB enumeration is proven.
