#!/usr/bin/env python3
"""Audit the source-built donor-era TWRP 3.3 image for SM-J720F."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
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
TRAILER_MARKER = b"SEANDROIDENFORCE"


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_header(blob: bytes) -> dict[str, object]:
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

    return {
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


def extract_ramdisk(ramdisk: bytes) -> tuple[list[str], dict[str, bytes]]:
    if not ramdisk.startswith(b"\x1f\x8b"):
        raise ValueError("ramdisk is not gzip-compressed")
    if shutil.which("cpio") is None:
        raise ValueError("cpio is required")

    with tempfile.TemporaryDirectory(prefix="j720f-legacy-audit-") as temp:
        base = Path(temp)
        cpio_data = gzip.decompress(ramdisk)
        cpio_path = base / "ramdisk.cpio"
        cpio_path.write_bytes(cpio_data)

        listing = subprocess.run(
            ["cpio", "-it"],
            cwd=base,
            input=cpio_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout.decode(errors="replace").splitlines()

        root = base / "root"
        root.mkdir()
        subprocess.run(
            ["cpio", "-idm", "--quiet"],
            cwd=root,
            input=cpio_data,
            check=True,
        )

        payloads: dict[str, bytes] = {}
        for relative in (
            "init",
            "default.prop",
            "etc/recovery.fstab",
            "fstab.samsungexynos7885",
            "init.recovery.service.rc",
            "init.recovery.samsungexynos7885.rc",
            "init.recovery.usb.rc",
            "ueventd.samsungexynos7885.rc",
            "sbin/recovery",
            "sbin/adbd",
            "sbin/j720f_usb.sh",
            "twres/portrait.xml",
            "sbin/libminuitwrp.so",
        ):
            path = root / relative
            if path.is_file():
                payloads[relative] = path.read_bytes()

        return listing, payloads


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
        header = parse_header(blob)
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

    cmdline = str(header["cmdline"]).split()
    for token in ("androidboot.selinux=permissive", "enforcing=0"):
        if token not in cmdline:
            errors.append(f"kernel command line is missing {token}")

    pos = PAGE
    kernel = blob[pos : pos + int(header["kernel_size"])]
    pos = align(pos + int(header["kernel_size"]), PAGE)
    ramdisk = blob[pos : pos + int(header["ramdisk_size"])]
    pos = align(pos + int(header["ramdisk_size"]), PAGE)
    pos = align(pos + int(header["second_size"]), PAGE)
    dt = blob[pos : pos + int(header["dt_size"])]

    if digest(kernel) != EXPECTED_KERNEL_SHA256:
        errors.append("kernel differs from the exact J720F Android 10 stock kernel")
    if digest(dt) != EXPECTED_DT_SHA256:
        errors.append("DT differs from the exact J720F Android 10 stock DT")
    if TRAILER_MARKER not in blob[-2048:]:
        errors.append("Samsung recovery trailer is missing")

    try:
        listing, payloads = extract_ramdisk(ramdisk)
    except Exception as exc:
        errors.append(f"ramdisk inspection failed: {exc}")
        listing, payloads = [], {}

    normalized = {item.lstrip("./") for item in listing}

    required_mountpoints = {
        "cache",
        "vendor",
        "odm",
        "efs",
        "cpefs",
        "preload",
        "omr",
    }
    for path in sorted(required_mountpoints - normalized):
        errors.append(f"generated ramdisk is missing mount point: /{path}")

    required = {
        "init",
        "default.prop",
        "etc/recovery.fstab",
        "fstab.samsungexynos7885",
        "init.recovery.service.rc",
        "init.recovery.samsungexynos7885.rc",
        "init.recovery.usb.rc",
        "ueventd.samsungexynos7885.rc",
        "sbin/recovery",
        "sbin/adbd",
        "sbin/j720f_usb.sh",
        "twres/portrait.xml",
        "sbin/libminuitwrp.so",
    }
    for path in sorted(required - normalized):
        errors.append(f"generated ramdisk is missing {path}")

    recovery = payloads.get("sbin/recovery", b"")
    if b"3.3.0-0" not in recovery:
        errors.append("recovery executable is not TWRP 3.3.0-0")

    service_rc = payloads.get("init.recovery.service.rc", b"").decode(errors="ignore")
    if "service recovery /sbin/recovery" not in service_rc:
        errors.append("generated service rc does not start /sbin/recovery")

    hardware_rc = payloads.get(
        "init.recovery.samsungexynos7885.rc", b""
    ).decode(errors="ignore")
    if "start set_permissive" not in hardware_rc:
        errors.append("hardware recovery rc does not start set_permissive")

    for forbidden_line in (
        "service j720f_usb_manual",
        "keycodes 114 115",
    ):
        if forbidden_line in hardware_rc:
            errors.append(
                f"obsolete USB keychord remains: {forbidden_line}"
            )

    usb_helper = payloads.get("sbin/j720f_usb.sh", b"").decode(
        errors="ignore"
    )
    for required_line in (
        "/sys/kernel/config/usb_gadget/g1",
        "functions/ffs.adb",
        "setprop ctl.restart adbd",
        "sys.usb.ffs.ready",
        "13600000.dwc3",
        "j720f-usb-current",
        "configfs-mounted",
        "ffs-timeout",
        "bind-failed",
    ):
        if required_line not in usb_helper:
            errors.append(
                f"manual ConfigFS helper is missing: {required_line}"
            )

    if "functions/adb.0" in usb_helper:
        errors.append("manual USB helper recreates duplicate adb.0")

    portrait = payloads.get("twres/portrait.xml", b"").decode(
        errors="ignore"
    )
    for required_line in (
        'name="Start J720F USB/ADB"',
        '<action function="cmd">/sbin/j720f_usb.sh</action>',
    ):
        if required_line not in portrait:
            errors.append(
                f"TWRP Advanced page is missing: {required_line}"
            )

    fstab = payloads.get("etc/recovery.fstab", b"").decode(errors="ignore")
    for forbidden in ("/carrier", "/external_sd", "/usb-otg"):
        if forbidden in fstab:
            errors.append(f"recovery fstab contains forbidden entry: {forbidden}")
    for required_mount in ("/system", "/vendor", "/odm", "/data", "/cache", "/efs"):
        if required_mount not in fstab:
            errors.append(f"recovery fstab is missing {required_mount}")

    usb = payloads.get("init.recovery.usb.rc", b"").decode(errors="ignore")
    if "on early-init\n    write /sys/fs/selinux/enforce 0" not in usb:
        errors.append("USB init rc does not force permissive during early-init")
    for required_line in (
        "setprop sys.usb.configfs 1",
        "setprop sys.usb.controller 13600000.dwc3",
        "mount configfs none /sys/kernel/config",
    ):
        if required_line not in usb:
            errors.append(f"USB init rc is missing: {required_line}")

    permissive_service = """service j720f_permissive /sbin/permissive.sh
    class core
    user root
    group root
    disabled
    oneshot
    seclabel u:r:init:s0
"""
    if "on init\n    start j720f_permissive" not in usb:
        errors.append("USB init rc does not start j720f_permissive during init")
    if permissive_service not in usb:
        errors.append("USB init rc does not run the permissive helper in init domain")
    for required_line in (
        "write /sys/class/android_usb/android0/idVendor 04E8",
        "write /sys/class/android_usb/android0/idProduct 6860",
        "write /sys/class/android_usb/android0/functions adb",
        "write /sys/class/android_usb/android0/functions mtp,adb",
        "write /sys/class/android_usb/android0/enable 1",
        "start adbd",
    ):
        if required_line not in usb:
            errors.append(f"legacy USB rc is missing: {required_line}")
    for forbidden in ("usb_gadget", "functions/adb.0", "functions/ffs.adb"):
        if forbidden in usb:
            errors.append(f"legacy USB rc unexpectedly contains {forbidden}")

    board = (args.tree / "BoardConfig.mk").read_text(errors="ignore")
    for required_setting in (
        'TARGET_RECOVERY_PIXEL_FORMAT := "ABGR_8888"',
        "RECOVERY_GRAPHICS_USE_LINELENGTH := true",
        "TW_USE_NEW_MINADBD := true",
        "TW_INCLUDE_CRYPTO := true",
        "TW_CRYPTO_USE_SYSTEM_VOLD := true",
        "BOARD_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy",
    ):
        if required_setting not in board:
            errors.append(f"BoardConfig.mk is missing: {required_setting}")
    if "TW_EXCLUDE_MTP" in board:
        errors.append("MTP is still excluded in BoardConfig.mk")

    recovery_policy_path = args.tree / "sepolicy/recovery.te"
    if not recovery_policy_path.is_file():
        errors.append("device recovery SELinux policy is missing")
    else:
        recovery_policy = recovery_policy_path.read_text(errors="ignore")
        if "permissive recovery;" not in recovery_policy:
            errors.append("recovery SELinux domain is not permissive")

    for obsolete in (
        "recovery/root/init.rc",
        "recovery/root/init.recovery.service.rc",
        "recovery/root/sbin/j720f_diag.sh",
    ):
        if (args.tree / obsolete).exists():
            errors.append(f"TWRP 9 bring-up override remains on legacy branch: {obsolete}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "image": str(args.image),
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
    (args.out_dir / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.out_dir / "ramdisk-files.txt").write_text("\n".join(listing) + "\n")
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
