#!/usr/bin/env python3
"""Extract the Android 10 recovery adbd runtime from the pinned CUL1 stock image.

The proprietary files are already present inside prebuilt/recovery-J720F-CUL1.img.lz4.
This script materializes only the adbd dependency closure into recovery/root/system
for the build; generated files remain untracked.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import shutil
import stat
import struct
import subprocess
import tempfile
from pathlib import Path

STOCK_LZ4_SHA256 = "28af7ed6508da206f5c649e8ad9afdd65043bb5241826d8135f2b26b2eabe24c"
STOCK_KERNEL_SHA256 = "f91660e294f4532d266d23f386f99f4e9c290859154236d82e5280af9f11d268"
STOCK_ADBD_SHA256 = "e5a1dff495b94d469ec4cfcda60efbc2a674c769acbf7c6447f5e994542ee84a"
STOCK_LINKER_SHA256 = "9904ebf793288ee34a1fe371f562e3ca923c24a1d1728af8c718b359b79e8e1d"

FILES = (
    "system/bin/adbd",
    "system/bin/linker64",
    "system/bin/sh",
    "system/etc/ld.config.txt",
    "system/lib64/ld-android.so",
    "system/lib64/libadbd.so",
    "system/lib64/libadbd_services.so",
    "system/lib64/libasyncio.so",
    "system/lib64/libbase.so",
    "system/lib64/libbootloader_message.so",
    "system/lib64/libc++.so",
    "system/lib64/libc.so",
    "system/lib64/libcap.so",
    "system/lib64/libcrypto.so",
    "system/lib64/libcrypto_utils.so",
    "system/lib64/libcutils.so",
    "system/lib64/libdl.so",
    "system/lib64/libext2_uuid.so",
    "system/lib64/libext4_utils.so",
    "system/lib64/libfec.so",
    "system/lib64/libfs_mgr.so",
    "system/lib64/liblog.so",
    "system/lib64/liblp.so",
    "system/lib64/libm.so",
    "system/lib64/libmdnssd.so",
    "system/lib64/libminijail.so",
    "system/lib64/libpackagelistparser.so",
    "system/lib64/libpcre2.so",
    "system/lib64/libselinux.so",
    "system/lib64/libsparse.so",
    "system/lib64/libsquashfs_utils.so",
    "system/lib64/libz.so",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unpack_boot_image(blob: bytes) -> tuple[bytes, bytes]:
    if blob[:8] != b"ANDROID!":
        raise ValueError("stock recovery is not a legacy Android boot image")
    kernel_size = struct.unpack_from("<I", blob, 8)[0]
    ramdisk_size = struct.unpack_from("<I", blob, 16)[0]
    page_size = struct.unpack_from("<I", blob, 36)[0]
    if page_size != 2048:
        raise ValueError(f"unexpected stock page size: {page_size}")
    kernel_off = page_size
    kernel = blob[kernel_off : kernel_off + kernel_size]
    ramdisk_off = ((kernel_off + kernel_size + page_size - 1) // page_size) * page_size
    ramdisk = blob[ramdisk_off : ramdisk_off + ramdisk_size]
    if sha256(kernel) != STOCK_KERNEL_SHA256:
        raise ValueError("stock recovery kernel hash mismatch")
    if not ramdisk.startswith(b"\x1f\x8b"):
        raise ValueError("stock recovery ramdisk is not gzip-compressed")
    return kernel, gzip.decompress(ramdisk)


def parse_newc(cpio: bytes) -> dict[str, tuple[int, bytes]]:
    entries: dict[str, tuple[int, bytes]] = {}
    pos = 0
    while True:
        if cpio[pos : pos + 6] not in (b"070701", b"070702"):
            raise ValueError(f"invalid newc header at offset {pos}")
        header = cpio[pos : pos + 110]
        fields = [int(header[6 + i * 8 : 14 + i * 8], 16) for i in range(13)]
        mode = fields[1]
        size = fields[6]
        name_size = fields[11]
        pos += 110
        raw_name = cpio[pos : pos + name_size]
        name = raw_name[:-1].decode("utf-8", "surrogateescape").lstrip("./")
        pos = (pos + name_size + 3) & ~3
        payload = cpio[pos : pos + size]
        pos = (pos + size + 3) & ~3
        if name == "TRAILER!!!":
            break
        entries[name] = (mode, payload)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stock_lz4", type=Path)
    parser.add_argument("recovery_root", type=Path)
    args = parser.parse_args()

    compressed = args.stock_lz4.read_bytes()
    if sha256(compressed) != STOCK_LZ4_SHA256:
        raise SystemExit("pinned CUL1 stock recovery LZ4 hash mismatch")

    with tempfile.TemporaryDirectory(prefix="j720f-stock-adbd-") as tmp:
        stock_img = Path(tmp) / "stock-recovery.img"
        lz4_binary = shutil.which("lz4")
        if lz4_binary:
            subprocess.run(
                [lz4_binary, "-d", "-f", str(args.stock_lz4), str(stock_img)],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            stock_blob = stock_img.read_bytes()
        else:
            try:
                import lz4.frame  # type: ignore
            except ImportError as exc:
                raise SystemExit("lz4 CLI or Python lz4 module is required") from exc
            stock_blob = lz4.frame.decompress(compressed)
        _, cpio = unpack_boot_image(stock_blob)

    entries = parse_newc(cpio)
    missing = [name for name in FILES if name not in entries]
    if missing:
        raise SystemExit(f"stock recovery is missing required adbd files: {missing}")

    system_out = args.recovery_root / "system"
    if system_out.exists():
        shutil.rmtree(system_out)

    for name in FILES:
        mode, payload = entries[name]
        if not stat.S_ISREG(mode):
            raise SystemExit(f"required stock entry is not a regular file: {name}")
        destination = args.recovery_root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        os.chmod(destination, stat.S_IMODE(mode))

    adbd = (args.recovery_root / "system/bin/adbd").read_bytes()
    linker = (args.recovery_root / "system/bin/linker64").read_bytes()
    if sha256(adbd) != STOCK_ADBD_SHA256:
        raise SystemExit("extracted Android 10 adbd hash mismatch")
    if sha256(linker) != STOCK_LINKER_SHA256:
        raise SystemExit("extracted Android 10 linker64 hash mismatch")

    marker = args.recovery_root / "system/etc/j720f-stock-adbd-bundle.txt"
    marker.write_text(
        "source=J720F CUL1 stock recovery\n"
        f"adbd_sha256={STOCK_ADBD_SHA256}\n"
        f"files={len(FILES)}\n"
    )
    print(f"extracted {len(FILES)} Android 10 adbd runtime files into {system_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
