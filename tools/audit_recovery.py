#!/usr/bin/env python3
"""Audit the forced-FunctionFS-entry TWRP 3.3 image for SM-J720F."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

LIMIT = 39_845_888
PAGE = 2048
EXPECTED_KERNEL_SHA256 = "f91660e294f4532d266d23f386f99f4e9c290859154236d82e5280af9f11d268"
EXPECTED_DT_SHA256 = "25fd9f99fcb520b117475c812302afdfd53f8f36dbcda6a9416429b2401ddafb"


def align(value: int, page: int = PAGE) -> int:
    return (value + page - 1) // page * page


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_image(blob: bytes) -> tuple[dict[str, object], bytes, bytes, bytes]:
    if blob[:8] != b"ANDROID!":
        raise ValueError("not a legacy Android boot image")

    (
        kernel_size,
        kernel_addr,
        ramdisk_size,
        ramdisk_addr,
        second_size,
        second_addr,
        tags_addr,
        page_size,
        dt_size,
        _unused,
    ) = struct.unpack_from("<10I", blob, 8)

    header = {
        "kernel_size": kernel_size,
        "kernel_addr": kernel_addr,
        "ramdisk_size": ramdisk_size,
        "ramdisk_addr": ramdisk_addr,
        "second_size": second_size,
        "second_addr": second_addr,
        "tags_addr": tags_addr,
        "page_size": page_size,
        "dt_size": dt_size,
        "name": blob[48:64].split(b"\0", 1)[0].decode("ascii", "replace"),
        "cmdline": blob[64:576].split(b"\0", 1)[0].decode("ascii", "replace"),
    }

    pos = page_size
    kernel = blob[pos : pos + kernel_size]
    pos = align(pos + kernel_size, page_size)
    ramdisk = blob[pos : pos + ramdisk_size]
    pos = align(pos + ramdisk_size, page_size)
    pos = align(pos + second_size, page_size)
    dt = blob[pos : pos + dt_size]
    return header, kernel, ramdisk, dt


def extract_ramdisk(ramdisk: bytes, root: Path) -> list[str]:
    if not ramdisk.startswith(b"\x1f\x8b"):
        raise ValueError("ramdisk is not gzip-compressed")
    if shutil.which("cpio") is None:
        raise ValueError("cpio is required")

    cpio_data = gzip.decompress(ramdisk)
    listing = subprocess.run(
        ["cpio", "-it"],
        input=cpio_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.decode(errors="replace").splitlines()

    root.mkdir()
    subprocess.run(
        ["cpio", "-idm", "--quiet", "--no-absolute-filenames"],
        cwd=root,
        input=cpio_data,
        check=True,
    )
    return listing


def read_text(root: Path, relative: str) -> str:
    path = root / relative
    return path.read_text(errors="ignore") if path.is_file() else ""


def require_contains(errors: list[str], text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label} is missing: {needle}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    blob = args.image.read_bytes()

    try:
        header, kernel, ramdisk, dt = parse_image(blob)
    except ValueError as exc:
        raise SystemExit(str(exc))

    if len(blob) > LIMIT:
        errors.append(f"image exceeds PIT limit: {len(blob)} > {LIMIT}")

    expected_header = {
        "kernel_addr": 0x10008000,
        "ramdisk_addr": 0x11000000,
        "second_addr": 0x10F00000,
        "tags_addr": 0x10000100,
        "page_size": PAGE,
        "dt_size": 628736,
        "name": "SRPRA09A005RU",
    }
    for key, expected in expected_header.items():
        if header[key] != expected:
            errors.append(f"header {key}={header[key]!r}; expected {expected!r}")

    if digest(kernel) != EXPECTED_KERNEL_SHA256:
        errors.append("kernel differs from the exact J720F Android 10 stock kernel")
    if digest(dt) != EXPECTED_DT_SHA256:
        errors.append("DT differs from the exact J720F Android 10 stock DT")

    trailer_path = args.tree / "prebuilt/samsung-recovery-trailer.bin"
    trailer = trailer_path.read_bytes()
    if not blob.endswith(trailer):
        errors.append("exact stock Samsung recovery trailer is missing")

    with tempfile.TemporaryDirectory(prefix="j720f-rc-audit-") as temp:
        root = Path(temp) / "root"
        try:
            listing = extract_ramdisk(ramdisk, root)
        except Exception as exc:
            errors.append(f"ramdisk inspection failed: {exc}")
            listing = []

        normalized = {item.lstrip("./") for item in listing}
        required_files = {
            "init",
            "init.rc",
            "default.prop",
            "etc/fstab",
            "etc/recovery.fstab",
            "fstab.samsungexynos7885",
            "init.recovery.service.rc",
            "init.recovery.usb.rc",
            "sepolicy",
            "sbin/recovery",
            "sbin/adbd",
            "sbin/libminuitwrp.so",
            "sbin/j720f_runtime_diag.sh",
            "sbin/j720f_collect_direct_usb_trace.sh",
            "sbin/blkid",
            "sbin/hexdump",
            "sbin/head",
        }
        for relative in sorted(required_files):
            if relative not in normalized and not (root / relative).is_file():
                errors.append(f"generated ramdisk is missing {relative}")

        for relative in ("external_sd", "external_sd/j720f.mountpoint"):
            if relative not in normalized and not (root / relative).exists():
                errors.append(f"generated ramdisk is missing {relative}")

        init_path = root / "init"
        if init_path.is_symlink():
            errors.append("/init unexpectedly points to stock Android init")
        elif not init_path.is_file() or not init_path.read_bytes().startswith(b"\x7fELF"):
            errors.append("/init is not the donor-era ELF init binary")
        elif b"J720F recovery: forcing SELinux permissive" in init_path.read_bytes():
            errors.append("/init still contains the disproven forced-permissive patch")

        recovery = (root / "sbin/recovery").read_bytes() if (root / "sbin/recovery").is_file() else b""
        if b"3.3.0-0" not in recovery:
            errors.append("/sbin/recovery is not TWRP 3.3.0-0")
        if b"/tmp/orsin" not in recovery or b"/tmp/orsout" not in recovery:
            errors.append("/sbin/recovery is missing the writable /tmp ORS FIFO paths")
        if b"/sbin/orsin" in recovery or b"/sbin/orsout" in recovery:
            errors.append("/sbin/recovery still embeds read-only /sbin ORS FIFO paths")

        adbd = (root / "sbin/adbd").read_bytes() if (root / "sbin/adbd").is_file() else b""
        for marker in (
            b"/tmp/J720F_ADBD_USB_TRACE.txt",
            b"J720F_USB_DIAG",
            b"J720F_MAIN_USB_GATE",
            b"J720F_MAIN_USB_DECISION",
            b"J720F_SHELL_CHILD phase=inherited_root_seclabel",
            b"J720F_SHELL_CHILD phase=pre_exec",
            b"/tmp/J720F_ADBD_TRACE.txt",
        ):
            if marker not in adbd:
                errors.append(f"instrumented /sbin/adbd is missing marker: {marker!r}")
        if b"/data/adb/adb-" in adbd:
            errors.append("instrumented /sbin/adbd still writes its native trace under /data")

        service_rc = read_text(root, "init.recovery.service.rc")
        require_contains(errors, service_rc, "service recovery /sbin/recovery", "recovery service rc")

        generated_fstab = root / "etc/fstab"
        if not generated_fstab.is_symlink():
            errors.append("/etc/fstab is not a symlink into writable tmpfs")
        elif os.readlink(generated_fstab) != "/tmp/fstab":
            errors.append(f"/etc/fstab points to {os.readlink(generated_fstab)!r}; expected '/tmp/fstab'")

        init_rc = read_text(root, "init.rc")
        if "init.recovery.vold_decrypt.rc" in init_rc:
            errors.append("init.rc still imports the absent vold decrypt rc")
        if "on property:service.adb.root=1" in init_rc:
            errors.append("init.rc still contains the legacy android_usb restart trigger")
        if "on property:ro.debuggable=1" in init_rc:
            errors.append("init.rc can still start adbd before the device USB action")
        if "write /sys/class/android_usb/android0/enable 1" in init_rc:
            errors.append("generic init.rc can still enable the Samsung USB gadget")
        require_contains(
            errors,
            init_rc,
            "setprop j720f.usb.native_prepare 1",
            "native FunctionFS init preparation",
        )
        require_contains(
            errors,
            init_rc,
            "service adbd /sbin/adbd --root_seclabel=u:r:su:s0 --device_banner=recovery",
            "stock-style native Android 7.1 root adbd service",
        )
        root_label_services = re.findall(
            r"(?m)^[ \t]*service[ \t]+adbd[ \t]+[^\n#]*--root_seclabel=[^ \t\n]+",
            init_rc,
        )
        if len(root_label_services) != 1 or "--root_seclabel=u:r:su:s0" not in root_label_services[0]:
            errors.append("init.rc does not use exactly the stock u:r:su:s0 root adbd label")
        if "/sbin/permissive.sh" in init_rc:
            errors.append("init.rc still invokes the obsolete late-permissive helper")

        merged_file_contexts = read_text(root, "file_contexts")
        require_contains(
            errors,
            merged_file_contexts,
            "/tmp/J720F_ADBD_USB_TRACE\\.txt",
            "merged recovery file_contexts",
        )
        require_contains(
            errors,
            merged_file_contexts,
            "/tmp/J720F_ADBD_TRACE\\.txt",
            "merged recovery file_contexts",
        )

        properties = read_text(root, "default.prop")
        for line in (
            "ro.secure=0",
            "ro.adb.secure=0",
            "ro.debuggable=1",
            "persist.sys.usb.config=adb",
        ):
            if line not in properties.splitlines():
                errors.append(f"default.prop is missing: {line}")
        if "persist.sys.usb.config=mtp" in properties:
            errors.append("default.prop still enables MTP")

        fstab = read_text(root, "etc/recovery.fstab")
        require_contains(errors, fstab, "/external_sd vfat /dev/block/mmcblk1p1 /dev/block/mmcblk1", "TWRP fstab")
        require_contains(errors, fstab, "/efs        emmc", "TWRP fstab")
        require_contains(errors, fstab, "/cpefs      emmc", "TWRP fstab")
        require_contains(errors, fstab, "/misc       emmc", "TWRP fstab")
        require_contains(errors, fstab, "flags=display=Misc;backup=1", "TWRP fstab")
        if "encryptable=footer" in fstab:
            errors.append("TWRP fstab still advertises the rejected legacy crypto footer")
        require_contains(errors, fstab, "length=-20480", "TWRP fstab")
        if "/efs        ext4" in fstab or "/cpefs      ext4" in fstab:
            errors.append("EFS/CPEFS are still configured as mountable ext4 filesystems")

        android_fstab = read_text(root, "fstab.samsungexynos7885")
        if "/EFS" in android_fstab or "/CPEFS" in android_fstab:
            errors.append("legacy init fstab still tries to mount EFS/CPEFS")
        if "encryptable=footer" in android_fstab:
            errors.append("legacy init fstab still mixes system-vold encryption handling")

        ueventd = read_text(root, "ueventd.samsungexynos7885.rc")
        for endpoint in ("/dev/usb-ffs/adb/ep0", "/dev/usb-ffs/adb/ep1", "/dev/usb-ffs/adb/ep2"):
            require_contains(errors, ueventd, endpoint, "FunctionFS endpoint permissions")

        usb = read_text(root, "init.recovery.usb.rc")
        for line in (
            "setprop sys.usb.configfs 1",
            "setprop sys.usb.controller 13600000.dwc3",
            "setprop sys.usb.ffs.ready 0",
            "setprop j720f.usb.transport native-android71-ffs",
            "setprop j720f.usb.adbd_domain_only 1",
            "setprop j720f.usb.direct_trace 1",
            "setprop j720f.usb.force_ffs_entry 1",
            "setprop j720f.usb.pure_configfs 0",
            "setprop j720f.usb.stock_android_usb_gate 1",
            "setprop j720f.usb.stock_link_order 1",
            "setprop persist.adb.trace_mask all",
            "write /tmp/J720F_ADBD_USB_TRACE.txt J720F_USB_DIAG_INIT_PRECREATED",
            "restorecon /tmp/J720F_ADBD_USB_TRACE.txt",
            "write /tmp/J720F_ADBD_TRACE.txt J720F_ADBD_TRACE_INIT_PRECREATED",
            "restorecon /tmp/J720F_ADBD_TRACE.txt",
            "setprop j720f.usb.trace_precreated 1",
            "mount configfs none /sys/kernel/config",
            "/sys/kernel/config/usb_gadget/g1/functions/ffs.adb",
            "/sys/kernel/config/usb_gadget/g1/configs/c.1/ffs.adb",
            "mount functionfs adb /dev/usb-ffs/adb uid=0,gid=0",
            "setprop j720f.usb.ffs_mounted 1",
            "service j7diag /sbin/sh /sbin/j720f_runtime_diag.sh",
            "on property:sys.usb.config=adb && property:sys.usb.ffs.ready=1",
            "write /sys/kernel/config/usb_gadget/g1/UDC ${sys.usb.controller}",
            "setprop j720f.usb.configfs_bind 1",
            "setprop j720f.usb.udc_bind_action 1",
            "setprop sys.usb.config adb",
            "on property:sys.usb.config=adb && property:sys.usb.configfs=1 && property:j720f.usb.ffs_mounted=1",
            "start adbd",
            "setprop j720f.usb.ffs_mount_action 1",
            "setprop j720f.usb.configfs_action 1",
        ):
            require_contains(errors, usb, line, "native Android 7.1 FunctionFS ADB rc")
        if "mount functionfs adb /dev/usb-ffs/adb uid=2000,gid=2000" in usb:
            errors.append("FunctionFS endpoints are still shell-owned while adbd runs as UID 0")

        ready_trigger = (
            "on property:sys.usb.config=adb && property:sys.usb.ffs.ready=1 "
            "&& property:sys.usb.configfs=1"
        )
        ready_index = usb.find(ready_trigger)
        mount_index = usb.find("mount functionfs adb /dev/usb-ffs/adb uid=0,gid=0")
        link_line = (
            "symlink /sys/kernel/config/usb_gadget/g1/functions/ffs.adb "
            "/sys/kernel/config/usb_gadget/g1/configs/c.1/ffs.adb"
        )
        link_index = usb.find(link_line)
        if min(link_index, mount_index, ready_index) < 0 or not (
            link_index < mount_index < ready_index
        ):
            errors.append(
                "ConfigFS ffs.adb link must be registered before the FunctionFS mount "
                "and preserved until the ffs.ready bind action"
            )
        if usb.count(link_line) != 1:
            errors.append("ConfigFS ffs.adb link must appear exactly once in the USB rc")
        if "rm /sys/kernel/config/usb_gadget/g1/configs/c.1/ffs.adb" in usb:
            errors.append("USB none action still removes the stock-order ffs.adb link")
        if "j720f.usb.pure_configfs_bind_action" in usb:
            errors.append("USB rc still uses an overlength Android 7 property name")
        for endpoint in ("ep0", "ep1", "ep2"):
            require_contains(
                errors,
                ueventd,
                f"/dev/usb-ffs/adb/{endpoint}                                 0600 root root",
                "root-owned FunctionFS endpoint permissions",
            )

        stock_gate = [
            "write /sys/class/android_usb/android0/enable 0",
            "write /sys/class/android_usb/android0/f_ffs/aliases adb",
            "write /sys/class/android_usb/android0/functions adb",
            "write /sys/class/android_usb/android0/enable 1",
        ]
        android_usb_lines = [
            line.strip() for line in usb.splitlines()
            if "/sys/class/android_usb/android0/" in line
        ]
        if android_usb_lines != stock_gate:
            errors.append(
                "native FunctionFS rc must contain exactly the four CUL1 stock "
                f"android_usb gate writes; found: {android_usb_lines}"
            )

        udc_bind = "write /sys/kernel/config/usb_gadget/g1/UDC ${sys.usb.controller}"
        ordered = [ready_trigger] + stock_gate[:3] + [udc_bind, stock_gate[3]]
        indices = [usb.find(item) for item in ordered]
        if min(indices) < 0 or indices != sorted(indices) or len(set(indices)) != len(indices):
            errors.append(
                "CUL1 android_usb gate must wrap the ConfigFS UDC bind in stock order"
            )

        for forbidden in (
            "mount configfs none /config",
            "functions/adb.0",
            "configs/c.1/adb.0",
            "/dev/android_adb",
        ):
            if forbidden in usb:
                errors.append(f"native FunctionFS rc contains rejected legacy ADB path: {forbidden}")
        if "/sys/fs/selinux/enforce" in usb or "/sbin/permissive.sh" in usb:
            errors.append("USB rc still contains the failed late-permissive workaround")
        if "mtp" in usb.lower():
            errors.append("USB rc still contains an MTP path")
        if "j720f_usb_report" in usb:
            errors.append("USB rc still relies on the failed init-domain report service")

        if (root / "sbin/postrecoveryboot.sh").exists():
            errors.append("blocking /sbin/postrecoveryboot.sh must not be packaged")

        diag = read_text(root, "sbin/j720f_runtime_diag.sh")
        for line in (
            "J720F_RUNTIME_DIAGNOSTICS.txt",
            "service_started=1",
            "DMESG USB/SELINUX",
            "NATIVE ANDROID 7.1 RECOVERY ADBD",
            "ADBD PROCESS / CONTEXT / FDS",
            "ADBD MAIN USB GATE / DIRECT FUNCTIONFS TRACE",
            "J720F_MAIN_USB_(GATE|DECISION)",
            "DIRECT ADBD FUNCTIONFS SYSCALL TRACE",
            "NATIVE ADB TRACE",
            "/tmp/J720F_ADBD_USB_TRACE.txt",
            "/tmp/J720F_ADBD_TRACE.txt",
            "j720f_collect_direct_usb_trace.sh auto",
            "pidof adbd",
            "/dev/usb-ffs/adb",
            "/sbin/adbd",
            "/sys/kernel/config/usb_gadget/g1/functions",
            "/sys/kernel/config/usb_gadget/g1",
            "/sys/class/android_usb/android0",
        ):
            require_contains(errors, diag, line, "safe init diagnostic service")
        for forbidden in (
            "/sbin/twrp",
            "ctl.stop",
            "ctl.start",
            "mount -t",
            "tune2fs",
        ):
            if forbidden in diag:
                errors.append(f"safe diagnostic script contains forbidden operation: {forbidden}")

        collector = read_text(root, "sbin/j720f_collect_direct_usb_trace.sh")
        for line in (
            "J720F_DIRECT_USB_TRACE",
            "J720F_ADBD_USB_TRACE.txt",
            "J720F_ADBD_TRACE.txt",
            "J720F_RUNTIME_DIAGNOSTICS.txt",
            "collection_summary.txt",
            "trace_metadata.txt",
            "data_access.txt",
            "main_usb_gate_lines=",
            "main_usb_decision_lines=",
        ):
            require_contains(errors, collector, line, "direct USB trace collector")
        for forbidden in ("mount -t", "ctl.stop", "ctl.start", "Format Data"):
            if forbidden in collector:
                errors.append(f"direct USB trace collector contains forbidden operation: {forbidden}")

        for line in (
            "service j7diag /sbin/sh /sbin/j720f_runtime_diag.sh",
            "group root shell readproc",
            "seclabel u:r:recovery:s0",
            "on property:init.svc.recovery=running",
            "setprop j720f.diag.triggered 1",
            "start j7diag",
        ):
            require_contains(errors, usb, line, "safe init diagnostic service rc")

        forbidden_ramdisk = {
            "init.recovery.vold_decrypt.rc",
            "sbin/libtwrpmtp-legacy.so",
            "system/bin/init",
            "system/bin/adbd",
            "system/bin/linker64",
            "system/lib64/libadbd.so",
            "system/.j720f_stock_adbd_bundle",
            "system/etc/j720f-stock-adbd-bundle.txt",
        }
        for relative in sorted(forbidden_ramdisk):
            if relative in normalized or (root / relative).exists():
                errors.append(f"forbidden mixed-userspace component remains: {relative}")

        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "ramdisk-files.txt").write_text("\n".join(listing) + "\n")

    board = (args.tree / "BoardConfig.mk").read_text(errors="ignore")
    for required_setting in (
        'TARGET_RECOVERY_PIXEL_FORMAT := "ABGR_8888"',
        "RECOVERY_GRAPHICS_USE_LINELENGTH := true",
        "TW_USE_NEW_MINADBD := true",
        "TW_INCLUDE_CRYPTO := true",
        "TW_EXCLUDE_MTP := true",
        "TW_DEFAULT_EXTERNAL_STORAGE := true",
    ):
        require_contains(errors, board, required_setting, "BoardConfig.mk")
    for forbidden_setting in ("TW_INCLUDE_FBE", "TW_CRYPTO_USE_SYSTEM_VOLD"):
        if forbidden_setting in board:
            errors.append(f"BoardConfig.mk still contains {forbidden_setting}")
    require_contains(
        errors,
        board,
        "BOARD_SEPOLICY_DIRS += device/samsung/j7duolte/sepolicy",
        "BoardConfig.mk",
    )

    init_policy = (args.tree / "sepolicy/init.te").read_text(errors="ignore")
    recovery_policy = (args.tree / "sepolicy/recovery.te").read_text(errors="ignore")
    adbd_policy = (args.tree / "sepolicy/adbd.te").read_text(errors="ignore")
    su_policy_path = args.tree / "sepolicy/su.te"
    if su_policy_path.exists():
        errors.append("device policy must not override the platform recovery su domain")
    all_device_policy = "\n".join((init_policy, recovery_policy, adbd_policy))
    for domain in ("init", "recovery"):
        if f"permissive {domain};" in all_device_policy:
            errors.append(f"device policy still declares {domain} permissive")
    if "permissive adbd;" in adbd_policy:
        errors.append("device adbd policy still relies on ineffective permissive mode")

    for rule in (
        "allow init configfs:file create_file_perms;",
        "allow init configfs:lnk_file create_file_perms;",
        "allow init sysfs_usb:file rw_file_perms;",
    ):
        require_contains(errors, init_policy, rule, "device init policy")
    require_contains(
        errors,
        init_policy,
        "allow init functionfs:filesystem { getattr mount remount unmount };",
        "device init FunctionFS policy",
    )

    for rule in (
        "allow adbd functionfs:file rw_file_perms;",
        "set_prop(adbd, ffs_prop)",
        "get_prop(adbd, twrp_prop)",
        "allow adbd self:process setcurrent;",
        "allow adbd su:process dyntransition;",
    ):
        require_contains(errors, adbd_policy, rule, "device native adbd startup policy")
    for stale_rule in (
        "allow adbd recovery:process",
        "allow recovery adbd:fd use;",
        "allow recovery adbd:unix_stream_socket",
        "domain_trans(adbd, rootfs, shell)",
        "allow adbd shell:process dyntransition;",
        "allow adbd shell:process noatsecure;",
        "allow shell rootfs:file rx_file_perms;",
        "allow shell adbd:fd use;",
        "allow shell adbd:unix_stream_socket { read write ioctl getattr };",
    ):
        if stale_rule in adbd_policy:
            errors.append(f"device adbd policy retains superseded command-child handoff: {stale_rule}")
    if "allow adbd tmpfs:" in adbd_policy:
        errors.append("device adbd policy still grants generic tmpfs access")
    if "adb_device:chr_file" in adbd_policy:
        errors.append("device adbd policy still targets the rejected legacy transport")

    policy = recovery_policy
    for rule in (
        "allow recovery vfat:dir create_dir_perms;",
        "allow recovery vfat:file create_file_perms;",
        "allow recovery self:netlink_kobject_uevent_socket create_socket_perms;",
        "allow recovery tmpfs:fifo_file create_file_perms;",
        "create_pty(recovery)",
        "set_prop(recovery, twrp_prop)",
        "set_prop(recovery, system_radio_prop)",
    ):
        require_contains(errors, policy, rule, "device recovery policy")

    trace_policy = (args.tree / "sepolicy/j720f_trace.te").read_text(errors="ignore")
    file_contexts = (args.tree / "sepolicy/file_contexts").read_text(errors="ignore")
    for rule in (
        "type j720f_adbd_trace_file, file_type;",
        "allow adbd j720f_adbd_trace_file:file create_file_perms;",
        "allow recovery j720f_adbd_trace_file:file r_file_perms;",
    ):
        require_contains(errors, trace_policy, rule, "shared trace-file policy")
    for trace_path in (
        "/tmp/J720F_ADBD_USB_TRACE\\.txt",
        "/tmp/J720F_ADBD_TRACE\\.txt",
    ):
        require_contains(errors, file_contexts, trace_path, "trace file_contexts")
    for rule in (
        "allow recovery system_data_file:dir create_dir_perms;",
        "allow recovery system_data_file:file create_file_perms;",
        "allow recovery media_rw_data_file:dir create_dir_perms;",
        "allow recovery media_rw_data_file:file create_file_perms;",
    ):
        require_contains(errors, recovery_policy, rule, "TWRP data-access policy")

    property_policy = (args.tree / "sepolicy/property.te").read_text(errors="ignore")
    property_contexts = (args.tree / "sepolicy/property_contexts").read_text(errors="ignore")
    require_contains(errors, property_policy, "type twrp_prop, property_type;", "device property policy")
    for prefix in ("ro.twrp.", "twrp.", "recovery.perf.", "j720f."):
        require_contains(errors, property_contexts, prefix, "device property contexts")

    runtime_diag = (args.tree / "recovery/root/sbin/j720f_runtime_diag.sh").read_text(errors="ignore")
    collector = (args.tree / "recovery/root/sbin/j720f_collect_direct_usb_trace.sh").read_text(errors="ignore")
    for script_name, script in (("runtime diagnostic", runtime_diag), ("trace collector", collector)):
        require_contains(errors, script, "/sbin/ls -ldZ /dev /dev/usb-ffs", script_name)
        require_contains(errors, script, "/dev/usb-ffs/adb/ep0", script_name)

    # Android 7.1 system/sepolicy/domain.te has an unconditional neverallow
    # that forbids domains from creating or writing rootfs-labelled files.
    # Keep the audit aligned with the compilable policy and reject any
    # accidental reintroduction of the forbidden workaround.
    if "allow recovery rootfs:" in policy:
        errors.append("device recovery policy contains forbidden rootfs write access")

    report = {
        "image": str(args.image),
        "layout": "Android 7.1 TWRP 3.3 stock-order ConfigFS ADB bind diagnostic with pinned CUL1 kernel/DT",
        "size": len(blob),
        "limit": LIMIT,
        "headroom": LIMIT - len(blob),
        "sha256": digest(blob),
        "header": header,
        "kernel_sha256": digest(kernel),
        "dt_sha256": digest(dt),
        "errors": errors,
        "warnings": warnings,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
