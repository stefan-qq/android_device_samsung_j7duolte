#!/sbin/sh
set -eu

G=/sys/kernel/config/usb_gadget/g1

case "${1:-}" in
    setup)
        mount -t configfs none /sys/kernel/config 2>/dev/null || true

        mkdir -p "$G"
        echo 0x04e8 > "$G/idVendor"
        echo 0x6860 > "$G/idProduct"
        echo 0x0404 > "$G/bcdDevice"
        echo 0x0200 > "$G/bcdUSB"

        mkdir -p "$G/strings/0x409"

        SERIAL="$(getprop ro.serialno)"
        [ -n "$SERIAL" ] || SERIAL=0123456789ABCDEF

        echo "$SERIAL" > "$G/strings/0x409/serialnumber"
        echo SAMSUNG > "$G/strings/0x409/manufacturer"
        echo SM-J720F_TWRP > "$G/strings/0x409/product"

        mkdir -p "$G/configs/c.1/strings/0x409"
        echo ADB > "$G/configs/c.1/strings/0x409/configuration"
        echo 0x3f > "$G/configs/c.1/MaxPower"

        mkdir -p "$G/functions/ffs.adb"

        if [ ! -L "$G/configs/c.1/ffs.adb" ]; then
            ln -s "$G/functions/ffs.adb" "$G/configs/c.1/ffs.adb"
        fi

        setprop sys.usb.j720f.configured 1
        ;;

    bind)
        echo 13600000.dwc3 > "$G/UDC"
        setprop sys.usb.state adb
        ;;

    disable)
        echo "" > "$G/UDC" 2>/dev/null || true
        setprop sys.usb.state none
        ;;

    *)
        echo "usage: $0 setup|bind|disable" >&2
        exit 2
        ;;
esac
