#!/usr/bin/env python3

import sys
from pathlib import Path


BUTTON_NAME = "Start J720F USB/ADB"
BUTTON_ACTION = '<action function="cmd">/sbin/j720f_usb.sh</action>'


def patch_theme(path: Path) -> bool:
    text = path.read_text()

    page_start = text.find('<page name="advanced">')
    if page_start < 0:
        return False

    page_end = text.find("</page>", page_start)
    if page_end < 0:
        raise RuntimeError(f"Unterminated advanced page: {path}")

    advanced_page = text[page_start:page_end]

    if BUTTON_NAME in advanced_page:
        return True

    listbox = text.find(
        '<listbox style="advanced_listbox">',
        page_start,
        page_end,
    )
    if listbox < 0:
        return False

    insert_at = text.find("\n", listbox)
    if insert_at < 0:
        raise RuntimeError(f"Malformed advanced listbox: {path}")

    insert_at += 1

    block = f'''\
\t\t\t\t<listitem name="{BUTTON_NAME}">
\t\t\t\t\t{BUTTON_ACTION}
\t\t\t\t</listitem>
'''

    path.write_text(text[:insert_at] + block + text[insert_at:])
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print(
            f"usage: {Path(sys.argv[0]).name} "
            "<bootable-recovery-directory>",
            file=sys.stderr,
        )
        return 2

    recovery_root = Path(sys.argv[1]).resolve()
    theme_root = recovery_root / "gui/theme"

    if not theme_root.is_dir():
        print(f"TWRP theme directory not found: {theme_root}", file=sys.stderr)
        return 1

    patched = []

    for path in sorted(theme_root.glob("*/portrait.xml")):
        if patch_theme(path):
            patched.append(path)

    if not patched:
        print("No compatible portrait TWRP themes were found", file=sys.stderr)
        return 1

    for path in patched:
        print(f"USB button present: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
