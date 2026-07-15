#!/usr/bin/env python3
"""Assemble J720F TWRP 3.3 on the stock Android 10 recovery ramdisk."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import tempfile

PAGE = 2048
LIMIT = 39_845_888
EXPECTED_KERNEL_SHA256 = "f91660e294f4532d266d23f386f99f4e9c290859154236d82e5280af9f11d268"
EXPECTED_DT_SHA256 = "25fd9f99fcb520b117475c812302afdfd53f8f36dbcda6a9416429b2401ddafb"
EXPECTED_STOCK_RECOVERY_SHA256 = "394df2c144f8e4b42495c353bc71ffbabf0fd5610087f80705bc59d111d55983"
EXPECTED_STOCK_INIT_SHA256 = "5b319a2a88742dd521bf041253dc7709d59206c5972023b398ea528396fa8da2"


def align(value: int, page: int = PAGE) -> int:
    return (value + page - 1) // page * page


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def split_image(blob: bytes) -> dict[str, object]:
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
        unused,
    ) = values

    if page_size != PAGE:
        raise ValueError(f"unexpected page size: {page_size}")

    pos = page_size
    kernel = blob[pos : pos + kernel_size]
    pos = align(pos + kernel_size, page_size)
    ramdisk = blob[pos : pos + ramdisk_size]
    pos = align(pos + ramdisk_size, page_size)
    second = blob[pos : pos + second_size]
    pos = align(pos + second_size, page_size)
    dt = blob[pos : pos + dt_size]

    return {
        "kernel": kernel,
        "ramdisk": ramdisk,
        "second": second,
        "dt": dt,
        "kernel_addr": kernel_addr,
        "ramdisk_addr": ramdisk_addr,
        "second_addr": second_addr,
        "tags_addr": tags_addr,
        "page_size": page_size,
        "unused": unused,
        "name": blob[48:64],
        "cmdline": blob[64:576],
        "extra": blob[608:1632],
    }


def extract_ramdisk(payload: bytes, destination: Path) -> None:
    if not payload.startswith(b"\x1f\x8b"):
        raise ValueError("ramdisk is not gzip-compressed")

    destination.mkdir(parents=True)
    cpio_data = gzip.decompress(payload)
    subprocess.run(
        ["cpio", "-idm", "--quiet", "--no-absolute-filenames"],
        cwd=destination,
        input=cpio_data,
        check=True,
    )


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def copy_entry(source: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        remove_path(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)

    if source.is_symlink():
        destination.symlink_to(os.readlink(source))
    elif source.is_dir():
        shutil.copytree(source, destination, symlinks=True, copy_function=shutil.copy2)
    else:
        shutil.copy2(source, destination, follow_symlinks=False)



def prune_stock_userspace(stock_root: Path) -> None:
    keep_system_bin = {
        "adbd",
        "init",
        "linker64",
        "ueventd",
    }
    keep_system_lib64 = {
        "ld-android.so",
        "libadbd.so",
        "libadbd_services.so",
        "libasyncio.so",
        "libbacktrace.so",
        "libbase.so",
        "libbootloader_message.so",
        "libc++.so",
        "libc.so",
        "libcap.so",
        "libcgrouprc.so",
        "libcrypto.so",
        "libcrypto_utils.so",
        "libcutils.so",
        "libdl.so",
        "libext2_uuid.so",
        "libext4_utils.so",
        "libfec.so",
        "libfs_mgr.so",
        "libfscrypt.so",
        "libgsi.so",
        "libhidl-gen-utils.so",
        "libjsoncpp.so",
        "libkeyutils.so",
        "liblog.so",
        "liblogwrap.so",
        "liblp.so",
        "liblzma.so",
        "libm.so",
        "libmdnssd.so",
        "libminijail.so",
        "libpackagelistparser.so",
        "libpcre2.so",
        "libprocessgroup.so",
        "libprocessgroup_setup.so",
        "libselinux.so",
        "libsparse.so",
        "libsquashfs_utils.so",
        "libunwindstack.so",
        "libz.so",
    }
    keep_system_etc = {
        "cgroups.json",
        "fota.cer",
        "ld.config.txt",
        "security",
    }

    for directory, keep in (
        (stock_root / "system/bin", keep_system_bin),
        (stock_root / "system/lib64", keep_system_lib64),
        (stock_root / "system/etc", keep_system_etc),
    ):
        for entry in list(directory.iterdir()):
            if entry.name not in keep:
                remove_path(entry)

    recovery_do = stock_root / "res/recovery.do"
    if recovery_do.exists():
        recovery_do.unlink()

def overlay_twrp(stock_root: Path, source_root: Path) -> None:
    stock_sbin = stock_root / "sbin"
    source_sbin = source_root / "sbin"
    stock_sbin.mkdir(exist_ok=True)

    excluded = {
        "j720f_configfs_mount",
        "j720f_usb.sh",
        "sswap",
    }
    for entry in sorted(source_sbin.iterdir(), key=lambda item: item.name):
        if entry.name in excluded:
            continue
        copy_entry(entry, stock_sbin / entry.name)

    copy_entry(source_root / "twres", stock_root / "twres")

    for relative in ("res/keys", "res/images"):
        candidate = source_root / relative
        if candidate.exists():
            copy_entry(candidate, stock_root / relative)

    copy_entry(
        source_root / "etc/recovery.fstab",
        stock_root / "system/etc/recovery.fstab",
    )
    copy_entry(
        source_root / "etc/mke2fs.conf",
        stock_root / "system/etc/mke2fs.conf",
    )
    copy_entry(
        source_root / "fstab.samsungexynos7885",
        stock_root / "fstab.samsungexynos7885",
    )

    for mountpoint in (
        "cache",
        "vendor",
        "odm",
        "efs",
        "cpefs",
        "preload",
        "omr",
    ):
        (stock_root / mountpoint).mkdir(parents=True, exist_ok=True)

    for obsolete in (
        stock_root / "sbin/j720f_usb.sh",
        stock_root / "sbin/j720f_configfs_mount",
    ):
        if obsolete.exists() or obsolete.is_symlink():
            remove_path(obsolete)

    portrait = stock_root / "twres/portrait.xml"
    portrait_text = portrait.read_text(errors="strict")
    portrait_text, count = re.subn(
        r"\n?[ \t]*<listitem name=\"Start J720F USB/ADB\">\s*"
        r"<action function=\"cmd\">/sbin/j720f_usb\.sh</action>\s*"
        r"</listitem>\n?",
        "\n",
        portrait_text,
        count=1,
    )
    if count > 1:
        raise ValueError("multiple obsolete USB diagnostic buttons found")
    portrait.write_text(portrait_text)


def patch_init(root: Path) -> None:
    path = root / "init.rc"
    text = path.read_text()

    old = "    setprop sys.usb.configfs 1\n"
    new = (
        "    setprop sys.usb.configfs 1\n"
        "    setprop sys.usb.controller 13600000.dwc3\n"
    )
    if "setprop sys.usb.controller 13600000.dwc3" not in text:
        if text.count(old) != 1:
            raise ValueError("stock ConfigFS property anchor is not unique")
        text = text.replace(old, new, 1)

    old = "service recovery /system/bin/recovery\n"
    new = "service recovery /sbin/recovery\n"
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise ValueError("stock recovery service anchor not found")

    adb_start = "on property:sys.usb.config=adb\n    start adbd\n"
    mtp_start = "on property:sys.usb.config=mtp,adb\n    start adbd\n"
    if mtp_start not in text:
        if text.count(adb_start) != 1:
            raise ValueError("stock ADB start trigger is not unique")
        text = text.replace(adb_start, adb_start + "\n" + mtp_start, 1)

    adb_ready_header = (
        "on property:sys.usb.config=adb && "
        "property:sys.usb.ffs.ready=1 && property:sys.usb.configfs=1\n"
    )
    mtp_ready_header = (
        "on property:sys.usb.config=mtp,adb && "
        "property:sys.usb.ffs.ready=1 && property:sys.usb.configfs=1\n"
    )
    if mtp_ready_header not in text:
        start = text.find(adb_ready_header)
        if start < 0:
            raise ValueError("stock ADB FunctionFS-ready trigger not found")
        end = text.find("\non property:", start + len(adb_ready_header))
        if end < 0:
            raise ValueError("end of stock ADB FunctionFS-ready trigger not found")
        block = text[start:end]
        mtp_block = block.replace(adb_ready_header, mtp_ready_header, 1)
        text = text[:end] + "\n" + mtp_block + text[end:]

    if "functions/adb.0" in text:
        raise ValueError("duplicate adb.0 function remains in stock-base init")

    path.write_text(text)


def patch_properties(root: Path) -> None:
    path = root / "prop.default"
    lines = path.read_text().splitlines()
    replacements = {
        "ro.secure": "0",
        "ro.adb.secure": "0",
        "ro.debuggable": "1",
        "persist.sys.usb.config": "adb",
    }
    seen: dict[str, int] = {key: 0 for key in replacements}
    output: list[str] = []

    for line in lines:
        key, separator, _value = line.partition("=")
        if separator and key in replacements:
            line = f"{key}={replacements[key]}"
            seen[key] += 1
        output.append(line)

    for key in ("ro.secure", "ro.adb.secure", "ro.debuggable"):
        if seen[key] != 1:
            raise ValueError(f"unexpected {key} count in stock properties: {seen[key]}")
    if seen["persist.sys.usb.config"] < 1:
        raise ValueError("stock properties contain no persist.sys.usb.config")

    path.write_text("\n".join(output) + "\n")


def normalize_mtimes(root: Path) -> None:
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        try:
            os.utime(path, (0, 0), follow_symlinks=False)
        except (NotImplementedError, PermissionError):
            pass
    os.utime(root, (0, 0), follow_symlinks=False)


def pack_ramdisk(root: Path) -> bytes:
    normalize_mtimes(root)
    command = (
        "find . -print0 | LC_ALL=C sort -z | "
        "cpio --null -o -H newc --owner=0:0 --reproducible --quiet"
    )
    result = subprocess.run(
        ["bash", "-c", command],
        cwd=root,
        stdout=subprocess.PIPE,
        check=True,
    )
    return gzip.compress(result.stdout, compresslevel=9, mtime=0)


def build_image(source: dict[str, object], ramdisk: bytes) -> bytes:
    kernel = source["kernel"]
    second = source["second"]
    dt = source["dt"]
    assert isinstance(kernel, bytes)
    assert isinstance(second, bytes)
    assert isinstance(dt, bytes)

    sha = hashlib.sha1()
    for payload in (kernel, ramdisk, second, dt):
        sha.update(payload)
        sha.update(struct.pack("<I", len(payload)))
    image_id = sha.digest() + b"\0" * 12

    header = (
        b"ANDROID!"
        + struct.pack(
            "<10I",
            len(kernel),
            int(source["kernel_addr"]),
            len(ramdisk),
            int(source["ramdisk_addr"]),
            len(second),
            int(source["second_addr"]),
            int(source["tags_addr"]),
            int(source["page_size"]),
            len(dt),
            int(source["unused"]),
        )
        + source["name"]
        + source["cmdline"]
        + image_id
        + source["extra"]
    )
    if len(header) != 1632:
        raise ValueError(f"unexpected legacy header size: {len(header)}")

    output = bytearray(header)
    output.extend(b"\0" * (PAGE - len(output)))
    for payload in (kernel, ramdisk, second, dt):
        output.extend(payload)
        output.extend(b"\0" * (align(len(payload)) - len(payload)))
    return bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    args = parser.parse_args()

    stock_blob = args.stock.read_bytes()
    source_blob = args.source.read_bytes()

    if sha256(stock_blob) != EXPECTED_STOCK_RECOVERY_SHA256:
        raise SystemExit("stock recovery image does not match J720F CUL1")

    stock = split_image(stock_blob)
    source = split_image(source_blob)

    for label, image in (("stock", stock), ("source", source)):
        if sha256(image["kernel"]) != EXPECTED_KERNEL_SHA256:
            raise SystemExit(f"{label} kernel does not match exact J720F stock kernel")
        if sha256(image["dt"]) != EXPECTED_DT_SHA256:
            raise SystemExit(f"{label} DT does not match exact J720F stock DT")

    context = (
        tempfile.TemporaryDirectory(prefix="j720f-stockbase-")
        if args.work_dir is None
        else None
    )
    base = Path(context.name) if context is not None else args.work_dir
    if base.exists() and args.work_dir is not None:
        shutil.rmtree(base)
    base.mkdir(parents=True)

    stock_root = base / "stock"
    source_root = base / "source"
    extract_ramdisk(stock["ramdisk"], stock_root)
    extract_ramdisk(source["ramdisk"], source_root)

    stock_init = stock_root / "system/bin/init"
    if sha256(stock_init.read_bytes()) != EXPECTED_STOCK_INIT_SHA256:
        raise SystemExit("stock ramdisk Android 10 init hash mismatch")

    prune_stock_userspace(stock_root)
    overlay_twrp(stock_root, source_root)
    patch_init(stock_root)
    patch_properties(stock_root)

    ramdisk = pack_ramdisk(stock_root)
    output = build_image(source, ramdisk)
    if len(output) > LIMIT:
        raise SystemExit(f"assembled image exceeds PIT limit before trailer: {len(output)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)

    print(f"stock={args.stock}")
    print(f"source={args.source}")
    print(f"output={args.output}")
    print(f"ramdisk_size={len(ramdisk)}")
    print(f"image_size_before_trailer={len(output)}")
    print(f"headroom_before_trailer={LIMIT - len(output)}")
    print(f"sha256_before_trailer={sha256(output)}")

    if context is not None:
        context.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
