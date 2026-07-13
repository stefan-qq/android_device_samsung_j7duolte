#!/usr/bin/env python3
"""Strict audit for the SM-J720F ADB-first diagnostic recovery image."""

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

    fields = struct.unpack_from("<10I", blob, 8)
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
    ) = fields

    name = blob[48:64].split(b"\0", 1)[0].decode("ascii", "replace")
    cmdline = blob[64:576].split(b"\0", 1)[0].decode("ascii", "replace")

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
        "name": name,
        "cmdline": cmdline,
    }


def cpio_listing(
    ramdisk: bytes,
) -> tuple[list[str], dict[str, str], dict[str, bytes]]:
    if not ramdisk.startswith(b"\x1f\x8b"):
        raise ValueError("recovery ramdisk is not gzip-compressed")

    if shutil.which("cpio") is None:
        raise ValueError("cpio is required for ramdisk audit")

    with tempfile.TemporaryDirectory(prefix="j720f-audit-") as temp:
        root = Path(temp)
        cpio_path = root / "ramdisk.cpio"
        cpio_path.write_bytes(gzip.decompress(ramdisk))

        listing = subprocess.run(
            ["cpio", "-it"],
            cwd=root,
            stdin=cpio_path.open("rb"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        ).stdout.splitlines()

        extract = root / "root"
        extract.mkdir()

        subprocess.run(
            ["cpio", "-idm", "--quiet"],
            cwd=extract,
            stdin=cpio_path.open("rb"),
            check=True,
        )

        # Inspect every generated rc file, including the root /init.rc. Strip
        # comments so disabled examples cannot satisfy or trip active checks.
        rc_files = {
            str(path.relative_to(extract)): "\n".join(
                line.split("#", 1)[0].rstrip()
                for line in path.read_text(errors="ignore").splitlines()
            )
            for path in sorted(extract.rglob("*.rc"))
            if path.is_file()
        }

        payloads: dict[str, bytes] = {}
        for relative in (
            "sbin/recovery",
            "sbin/libminuitwrp.so",
        ):
            candidate = extract / relative
            if candidate.is_file():
                payloads[relative] = candidate.read_bytes()

        return listing, rc_files, payloads


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("recovery-audit"),
    )
    parser.add_argument("--tree", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    blob = args.image.read_bytes()

    try:
        hdr = parse_header(blob)
    except ValueError as exc:
        raise SystemExit(str(exc))

    if len(blob) > LIMIT:
        errors.append(f"image exceeds PIT limit: {len(blob)} > {LIMIT}")

    if hdr["page_size"] != PAGE:
        errors.append(f"page size {hdr['page_size']} != {PAGE}")

    cmdline_tokens = str(hdr["cmdline"]).split()

    if "androidboot.selinux=permissive" not in cmdline_tokens:
        errors.append(
            "recovery command line is missing "
            "androidboot.selinux=permissive"
        )

    if "enforcing=0" not in cmdline_tokens:
        errors.append(
            "recovery command line is missing enforcing=0"
        )

    expected = {
        "kernel_addr": 0x10008000,
        "ramdisk_addr": 0x11000000,
        "second_addr": 0x10F00000,
        "tags_addr": 0x10000100,
        "name": "SRPRA09A005RU",
        "dt_size": 628736,
    }

    for key, value in expected.items():
        if hdr[key] != value:
            errors.append(
                f"header {key}={hdr[key]!r}; expected {value!r}"
            )

    pos = PAGE

    kernel = blob[pos : pos + int(hdr["kernel_size"])]
    pos = align(pos + int(hdr["kernel_size"]), PAGE)

    ramdisk = blob[pos : pos + int(hdr["ramdisk_size"])]
    pos = align(pos + int(hdr["ramdisk_size"]), PAGE)

    pos = align(pos + int(hdr["second_size"]), PAGE)
    dt = blob[pos : pos + int(hdr["dt_size"])]

    if digest(kernel) != EXPECTED_KERNEL_SHA256:
        errors.append(
            "kernel hash differs from stock J720F Android 10 kernel"
        )

    if digest(dt) != EXPECTED_DT_SHA256:
        errors.append(
            "DT hash differs from exact stock J720F DT payload"
        )

    if (
        not blob.endswith(TRAILER_MARKER)
        and TRAILER_MARKER not in blob[-2048:]
    ):
        errors.append("stock Samsung recovery trailer is missing")

    try:
        listing, rc_files, payloads = cpio_listing(ramdisk)
    except Exception as exc:
        # The audit must report ramdisk failures rather than silently skip them.
        errors.append(f"ramdisk inspection failed: {exc}")
        listing, rc_files, payloads = [], {}, {}

    rc_text = "\n".join(rc_files.values())
    rc_lines = [
        line.strip()
        for line in rc_text.splitlines()
        if line.strip()
    ]

    root_init_lines = [
        line.strip()
        for line in rc_files.get("init.rc", "").splitlines()
        if line.strip()
    ]

    usb_init_lines = [
        line.strip()
        for line in rc_files.get(
            "init.recovery.usb.rc",
            "",
        ).splitlines()
        if line.strip()
    ]

    required_any = {
        "TWRP recovery executable": {
            "sbin/recovery",
            "system/bin/recovery",
        },
        "adbd": {
            "sbin/adbd",
            "system/bin/adbd",
        },
        "recovery fstab": {
            "etc/recovery.fstab",
            "system/etc/recovery.fstab",
        },
        "device USB rc": {
            "init.recovery.usb.rc",
        },
        "device recovery service rc": {
            "init.recovery.service.rc",
        },
        "ADB-first diagnostic script": {
            "sbin/j720f_diag.sh",
        },
        "hardware init rc": {
            "init.recovery.samsungexynos7885.rc",
        },
        "hardware ueventd rc": {
            "ueventd.samsungexynos7885.rc",
        },
    }

    normalized = {
        item.lstrip("./")
        for item in listing
    }

    for label, choices in required_any.items():
        if not normalized.intersection(choices):
            errors.append(
                f"missing {label}: expected one of {sorted(choices)}"
            )

    recovery_binary = payloads.get("sbin/recovery", b"")
    minui_binary = payloads.get("sbin/libminuitwrp.so", b"")
    brightness_path = (
        b"/sys/devices/14800000.dsim/backlight/panel/brightness"
    )

    if brightness_path not in recovery_binary:
        errors.append(
            "finished sbin/recovery does not contain the J720F panel "
            "brightness path"
        )

    if b"setting DRM_FORMAT_ABGR8888" not in minui_binary:
        errors.append(
            "finished libminuitwrp.so does not contain ABGR_8888 "
            "framebuffer support"
        )

    service_init_lines = [
        line.strip()
        for line in rc_files.get(
            "init.recovery.service.rc",
            "",
        ).splitlines()
        if line.strip()
    ]

    hardware_init_lines = [
        line.strip()
        for line in rc_files.get(
            "init.recovery.samsungexynos7885.rc",
            "",
        ).splitlines()
        if line.strip()
    ]

    if "service recovery /sbin/recovery" not in service_init_lines:
        errors.append(
            "diagnostic service rc does not define /sbin/recovery"
        )

    if "disabled" in service_init_lines:
        errors.append(
            "recovery service is still disabled; this build must start "
            "/sbin/recovery normally"
        )

    if hardware_init_lines.count("start j720f_diag") != 1:
        errors.append(
            "hardware init must start j720f_diag exactly once"
        )

    if not any(
        line.startswith("service j720f_diag ")
        for line in hardware_init_lines
    ):
        errors.append(
            "hardware init does not define the j720f_diag service"
        )

    if root_init_lines.count("start set_permissive") != 2:
        errors.append(
            "root /init.rc must start set_permissive exactly twice "
            "(during init and boot)"
        )

    for required_line in (
        "mkdir /dev/pts 0755 root root",
        "mount devpts devpts /dev/pts",
    ):
        if required_line not in root_init_lines:
            errors.append(
                f"root /init.rc is missing: {required_line}"
            )

    forbidden_line = "setprop service.adb.root 1"
    if forbidden_line in rc_lines:
        errors.append(
            f"generated ramdisk contains forbidden action: "
            f"{forbidden_line}"
        )

    disable_line = "write /sys/class/android_usb/android0/enable 0"
    enable_line = "write /sys/class/android_usb/android0/enable 1"

    if (
        rc_lines.count(disable_line) != 2
        or usb_init_lines.count(disable_line) != 2
    ):
        errors.append(
            "expected exactly two android0 enable=0 writes, owned by "
            "init.recovery.usb.rc"
        )

    if (
        rc_lines.count(enable_line) != 1
        or usb_init_lines.count(enable_line) != 1
    ):
        errors.append(
            "expected exactly one stock Samsung android0 enable=1 "
            "bridge action, owned by init.recovery.usb.rc"
        )

    for required_bridge_line in (
        "write /sys/class/android_usb/android0/f_ffs/aliases adb",
        "write /sys/class/android_usb/android0/functions adb",
    ):
        if (
            rc_lines.count(required_bridge_line) != 1
            or usb_init_lines.count(required_bridge_line) != 1
        ):
            errors.append(
                "missing or duplicated stock Samsung USB bridge action: "
                f"{required_bridge_line}"
            )

    ffs_prefix = (
        "mkdir /sys/kernel/config/usb_gadget/g1/functions/ffs.adb"
    )

    ffs_creations = [
        line
        for line in rc_lines
        if line.startswith(ffs_prefix)
    ]

    usb_ffs_creations = [
        line
        for line in usb_init_lines
        if line.startswith(ffs_prefix)
    ]

    if (
        len(ffs_creations) != 1
        or len(usb_ffs_creations) != 1
    ):
        errors.append(
            "expected exactly one ffs.adb function creation, "
            "owned by init.recovery.usb.rc"
        )

    if any(
        "functions/adb.0" in line
        for line in rc_lines
    ):
        errors.append(
            "legacy adb.0 gadget found; first bring-up must use "
            "only ffs.adb"
        )

    mtp_markers = (
        "/functions/mtp",
        "sys.usb.config=mtp",
        "setprop sys.usb.config mtp",
        "start mtpd",
    )

    if any(
        marker in line
        for marker in mtp_markers
        for line in rc_lines
    ):
        errors.append(
            "MTP gadget configuration found; first bring-up "
            "must remain ADB-only"
        )

    udc_bind = (
        "write /sys/kernel/config/usb_gadget/g1/UDC "
        "${sys.usb.controller}"
    )

    if (
        rc_lines.count(udc_bind) != 1
        or usb_init_lines.count(udc_bind) != 1
    ):
        errors.append(
            "expected exactly one active UDC bind to "
            "${sys.usb.controller}, owned by init.recovery.usb.rc"
        )

    controller_line = (
        "setprop sys.usb.controller 13600000.dwc3"
    )

    if rc_lines.count(controller_line) != 1:
        errors.append(
            "USB controller 13600000.dwc3 must be set exactly once"
        )

    if (
        "/sys/class/android_usb/android0/f_ffs/aliases"
        not in rc_text
    ):
        errors.append(
            "Samsung android_usb FunctionFS alias gate is missing"
        )

    if args.tree:
        board = (
            args.tree / "BoardConfig.mk"
        ).read_text(errors="ignore")

        for required_board_line in (
            'TARGET_RECOVERY_PIXEL_FORMAT := "ABGR_8888"',
            'TW_BRIGHTNESS_PATH := "/sys/devices/14800000.dsim/backlight/panel/brightness"',
            "TW_MAX_BRIGHTNESS := 255",
            "TW_DEFAULT_BRIGHTNESS := 153",
        ):
            if required_board_line not in board:
                errors.append(
                    "BoardConfig.mk is missing known-good display setting: "
                    f"{required_board_line}"
                )

        if "BOARD_PREBUILT_RECOVERY_RAMDISK" in board:
            errors.append(
                "device tree still enables "
                "BOARD_PREBUILT_RECOVERY_RAMDISK"
            )

        device_init = args.tree / "recovery/root/init.rc"

        if not device_init.is_file():
            errors.append(
                "device-owned recovery/root/init.rc is missing"
            )

        for obsolete in (
            "recovery/root/ueventd.rc",
            "recovery/root/sepolicy_version",
        ):
            if (args.tree / obsolete).exists():
                errors.append(
                    f"obsolete top-level override still exists: "
                    f"{obsolete}"
                )

        stale_hardware_files = (
            "recovery/root/init.recovery.exynos7884.rc",
            "recovery/root/ueventd.exynos7884.rc",
        )

        for stale in stale_hardware_files:
            if (args.tree / stale).exists():
                errors.append(
                    f"stale hardware-specific rc remains: {stale}"
                )

        device_mk = (
            args.tree / "device.mk"
        ).read_text(errors="ignore")

        if "ro.hardware=samsungexynos7885" not in device_mk:
            errors.append(
                "device.mk does not use stock "
                "ro.hardware=samsungexynos7885"
            )

        if (
            b"androidboot.hardware=samsungexynos7885"
            not in dt
        ):
            errors.append(
                "DT does not advertise stock "
                "samsungexynos7885 hardware name"
            )

    args.out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        "image": str(args.image),
        "size": len(blob),
        "limit": LIMIT,
        "headroom": LIMIT - len(blob),
        "sha256": digest(blob),
        "header": hdr,
        "kernel_sha256": digest(kernel),
        "dt_sha256": digest(dt),
        "errors": errors,
        "warnings": warnings,
    }

    (
        args.out_dir / "audit.json"
    ).write_text(
        json.dumps(report, indent=2) + "\n"
    )

    (
        args.out_dir / "ramdisk-files.txt"
    ).write_text(
        "\n".join(listing) + "\n"
    )

    (
        args.out_dir / "sha256.txt"
    ).write_text(
        f"{digest(blob)}  {args.image.name}\n"
    )

    print(json.dumps(report, indent=2))

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
