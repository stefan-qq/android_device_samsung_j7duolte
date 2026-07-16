#!/usr/bin/env python3
"""Audit the stock-Android-10-base TWRP 3.3 image for SM-J720F."""

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
EXPECTED_STOCK_HASHES = {
    "system/bin/init": "5b319a2a88742dd521bf041253dc7709d59206c5972023b398ea528396fa8da2",
    "system/bin/adbd": "e5a1dff495b94d469ec4cfcda60efbc2a674c769acbf7c6447f5e994542ee84a",
    "sepolicy": "310ecd33e63988390780c913b6036ce4896f9cc6e388daf6270e80720949732e",
    "ueventd.rc": "c445126003ec52d30cdb0615fbc9507ba726044b54f0ff2aac89ffba2da3e792",
    "plat_file_contexts": "813a3998fda03cd75947028da5f60968332696f6e3c09d92882f7aebf035d9df",
    "plat_property_contexts": "af9d89be335803791f42c6b9d850d3f886d753b8e4099edd7e1e3386784c67d4",
    "vendor_file_contexts": "fc57a5385988d5ce41e1cc61f8ac906ed8a0d77cc519eb39039b3ea6ccad8866",
    "vendor_property_contexts": "fe1a8770659e4d633261ed03a0f362f7eab238498a94959739bc459ac3892766",
    "system/bin/sh": "0481eb8f49f14fd11ff76df2c6a5bf750b12870f858ff8f9bf88832f6ce972be",
    "system/bin/toybox": "bea181efaec3b3c95018c1dd98ad8b5784c373a6d084404d19c7d1d3a76c389d",
    "system/lib64/libhidlbase.so": "8e7ac22d0959d7480043f33d9408ab80abbae70c3224140caf5990867bbda9bc",
}


def align(value: int, page: int = PAGE) -> int:
    return (value + page - 1) // page * page


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_image(blob: bytes) -> tuple[dict[str, object], bytes, bytes, bytes]:
    if blob[:8] != b"ANDROID!":
        raise ValueError("not a legacy Android boot image")

    values = struct.unpack_from("<10I", blob, 8)
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
    ) = values

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

    with tempfile.TemporaryDirectory(prefix="j720f-stockbase-audit-") as temp:
        root = Path(temp) / "root"
        try:
            listing = extract_ramdisk(ramdisk, root)
        except Exception as exc:
            errors.append(f"ramdisk inspection failed: {exc}")
            listing = []

        normalized = {item.lstrip("./") for item in listing}

        required_dirs = {
            "cache",
            "vendor",
            "odm",
            "efs",
            "cpefs",
            "preload",
            "omr",
            "sbin",
            "system/bin",
            "system/lib64",
            "twres",
        }
        for relative in sorted(required_dirs):
            if not (root / relative).is_dir():
                errors.append(f"ramdisk is missing directory: /{relative}")

        required_files = {
            "init.rc",
            "prop.default",
            "sepolicy",
            "ueventd.rc",
            "fstab.samsungexynos7885",
            "system/bin/init",
            "system/bin/adbd",
            "system/bin/linker64",
            "system/bin/sh",
            "system/bin/toybox",
            "system/lib64/libhidlbase.so",
            "system/etc/recovery.fstab",
            "sbin/recovery",
            "sbin/libminuitwrp.so",
            "twres/portrait.xml",
        }
        for relative in sorted(required_files):
            if not (root / relative).is_file():
                errors.append(f"ramdisk is missing file: /{relative}")

        init_link = root / "init"
        if not init_link.is_symlink() or os.readlink(init_link) != "/system/bin/init":
            errors.append("/init is not the stock /system/bin/init symlink")

        default_link = root / "default.prop"
        if not default_link.is_symlink() or os.readlink(default_link) != "prop.default":
            errors.append("/default.prop is not the stock prop.default symlink")

        for relative, expected in EXPECTED_STOCK_HASHES.items():
            path = root / relative
            if not path.is_file() or digest(path.read_bytes()) != expected:
                errors.append(f"stock Android 10 component differs: /{relative}")

        recovery = (root / "sbin/recovery").read_bytes() if (root / "sbin/recovery").is_file() else b""
        if b"3.3.0-0" not in recovery:
            errors.append("/sbin/recovery is not TWRP 3.3.0-0")

        init_rc = read_text(root, "init.rc")
        required_init = (
            "service recovery /sbin/recovery",
            "setenv PATH /sbin:/system/bin",
            "setenv LD_LIBRARY_PATH /sbin",
            "wait /dev/block/platform/13500000.dwmmc0/by-name/CACHE 10",
            "mount ext4 /dev/block/platform/13500000.dwmmc0/by-name/CACHE /cache",
            "write /cache/j720f-v23-init-fs reached",
            "write /cache/j720f-v23-init-boot reached",
            "write /cache/j720f-v23-ueventd-state ${init.svc.ueventd}",
            "write /cache/j720f-v23-recovery-running reached",
            "write /cache/j720f-v23-recovery-stopped reached",
            "write /cache/j720f-v23-adbd-running reached",
            "service adbd /system/bin/adbd",
            "setprop sys.usb.configfs 1",
            "setprop sys.usb.controller 13600000.dwc3",
            "mount configfs none /sys/kernel/config",
            "functions/ffs.adb",
            "mount functionfs adb /dev/usb-ffs/adb uid=2000,gid=2000",
            "on property:sys.usb.config=mtp,adb",
            "on property:sys.usb.config=mtp,adb && property:sys.usb.ffs.ready=1 && property:sys.usb.configfs=1",
            "write /sys/kernel/config/usb_gadget/g1/UDC ${sys.usb.controller}",
        )
        for line in required_init:
            if line not in init_rc:
                errors.append(f"stock-base init.rc is missing: {line}")
        if "functions/adb.0" in init_rc:
            errors.append("stock-base init.rc contains duplicate adb.0")

        if "export LD_LIBRARY_PATH /sbin" in init_rc:
            errors.append(
                "global LD_LIBRARY_PATH would poison stock Android 10 services"
            )
        if "export PATH /sbin:/system/bin" in init_rc:
            errors.append(
                "global TWRP PATH must not be inherited by stock services"
            )
        if (root / "sbin/j720f_recovery_wrapper.sh").exists():
            errors.append("obsolete shell recovery wrapper remains")

        if (root / "system/bin/recovery").exists():
            errors.append("unused stock /system/bin/recovery remains")

        properties = read_text(root, "prop.default")
        for line in (
            "ro.secure=0",
            "ro.adb.secure=0",
            "ro.debuggable=1",
            "persist.sys.usb.config=adb",
        ):
            if line not in properties.splitlines():
                errors.append(f"stock-base properties are missing: {line}")

        fstab = read_text(root, "system/etc/recovery.fstab")
        for forbidden in ("/carrier", "/external_sd", "/usb-otg"):
            if forbidden in fstab:
                errors.append(f"TWRP fstab contains forbidden entry: {forbidden}")
        for mountpoint in ("/system", "/vendor", "/odm", "/data", "/cache", "/efs"):
            if mountpoint not in fstab:
                errors.append(f"TWRP fstab is missing {mountpoint}")

        for obsolete in (
            "sbin/j720f_usb.sh",
            "sbin/j720f_configfs_mount",
        ):
            if obsolete in normalized or (root / obsolete).exists():
                errors.append(f"obsolete USB diagnostic remains: /{obsolete}")

        portrait = read_text(root, "twres/portrait.xml")
        if "Start J720F USB/ADB" in portrait or "j720f_usb.sh" in portrait:
            errors.append("obsolete USB diagnostic button remains in TWRP theme")

        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "ramdisk-files.txt").write_text("\n".join(listing) + "\n")

    report = {
        "image": str(args.image),
        "layout": "stock Android 10 services with recovery-only TWRP 3.3 environment",
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
