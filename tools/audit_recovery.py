#!/usr/bin/env python3
"""Audit the source-built donor-era TWRP 3.3 image for SM-J720F."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
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

    for token in ("androidboot.selinux=permissive", "enforcing=0"):
        if token not in str(header["cmdline"]).split():
            errors.append(f"kernel command line is missing {token}")

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

        recovery = (root / "sbin/recovery").read_bytes() if (root / "sbin/recovery").is_file() else b""
        if b"3.3.0-0" not in recovery:
            errors.append("/sbin/recovery is not TWRP 3.3.0-0")

        service_rc = read_text(root, "init.recovery.service.rc")
        require_contains(errors, service_rc, "service recovery /sbin/recovery", "recovery service rc")

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
        require_contains(errors, fstab, "encryptable=footer", "TWRP fstab")
        if "/efs        ext4" in fstab or "/cpefs      ext4" in fstab:
            errors.append("EFS/CPEFS are still configured as mountable ext4 filesystems")

        android_fstab = read_text(root, "fstab.samsungexynos7885")
        if "/EFS" in android_fstab or "/CPEFS" in android_fstab:
            errors.append("legacy init fstab still tries to mount EFS/CPEFS")
        if "encryptable=footer" in android_fstab:
            errors.append("legacy init fstab still mixes system-vold encryption handling")

        usb = read_text(root, "init.recovery.usb.rc")
        for line in (
            "setprop sys.usb.configfs 1",
            "setprop sys.usb.controller 13600000.dwc3",
            "mount configfs none /sys/kernel/config",
            "functions/ffs.adb",
            "mount functionfs adb /dev/usb-ffs/adb uid=2000,gid=2000",
            "write /sys/kernel/config/usb_gadget/g1/UDC ${sys.usb.controller}",
            "setprop sys.usb.config adb",
            "start adbd",
        ):
            require_contains(errors, usb, line, "ADB-only ConfigFS rc")
        if "mtp" in usb.lower():
            errors.append("USB rc still contains an MTP path")

        forbidden_ramdisk = {
            "init.recovery.vold_decrypt.rc",
            "sbin/libtwrpmtp-legacy.so",
            "system/bin/init",
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
    ):
        require_contains(errors, board, required_setting, "BoardConfig.mk")
    for forbidden_setting in ("TW_INCLUDE_FBE", "TW_CRYPTO_USE_SYSTEM_VOLD"):
        if forbidden_setting in board:
            errors.append(f"BoardConfig.mk still contains {forbidden_setting}")

    policy = (args.tree / "sepolicy/recovery.te").read_text(errors="ignore")
    for rule in (
        "allow recovery vfat:dir create_dir_perms;",
        "allow recovery vfat:file create_file_perms;",
        "allow recovery self:netlink_kobject_uevent_socket create_socket_perms;",
    ):
        require_contains(errors, policy, rule, "device recovery policy")

    # Android 7.1 system/sepolicy/domain.te has an unconditional neverallow
    # that forbids domains from creating or writing rootfs-labelled files.
    # Keep the audit aligned with the compilable policy and reject any
    # accidental reintroduction of the forbidden workaround.
    if "allow recovery rootfs:" in policy:
        errors.append("device recovery policy contains forbidden rootfs write access")

    report = {
        "image": str(args.image),
        "layout": "source-built Android 7.1 donor-era TWRP 3.3 userspace",
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
