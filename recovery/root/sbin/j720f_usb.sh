#!/sbin/sh

LOG=/tmp/j720f-usb.log
exec > "$LOG" 2>&1
set -x

G=/sys/kernel/config/usb_gadget/g1

mark()
{
    STAGE="$1"

    rm -f /tmp/j720f-usb-current 2>/dev/null || true
    echo "$STAGE" > /tmp/j720f-usb-current
    touch "/tmp/j720f-usb-$STAGE"
    setprop sys.usb.j720f.stage "$STAGE"

    if [ -d /cache ]; then
        rm -f /cache/j720f-usb-current 2>/dev/null || true
        echo "$STAGE" > /cache/j720f-usb-current 2>/dev/null || true
        touch "/cache/j720f-usb-$STAGE" 2>/dev/null || true
    fi
}

fail()
{
    mark "$1"
    exit 1
}

rm -f /tmp/j720f-usb-* /cache/j720f-usb-* 2>/dev/null || true
mark triggered

# Disable the inactive legacy Samsung gadget after TWRP is fully started.
if [ -e /sys/class/android_usb/android0/enable ]; then
    echo 0 > /sys/class/android_usb/android0/enable 2>/dev/null || true
fi

mkdir -p /sys/kernel/config
mount -t configfs none /sys/kernel/config 2>/dev/null || true

[ -d /sys/kernel/config/usb_gadget ] || fail configfs-missing

mkdir -p "$G" || fail gadget-create-failed

if [ -e "$G/UDC" ]; then
    echo "" > "$G/UDC" 2>/dev/null || true
fi

echo 0x04e8 > "$G/idVendor" ||
    fail vendor-write-failed

echo 0x6860 > "$G/idProduct" ||
    fail product-write-failed

mkdir -p "$G/strings/0x409" ||
    fail strings-create-failed

SERIAL="$(getprop ro.serialno)"
[ -n "$SERIAL" ] || SERIAL=0123456789ABCDEF

echo "$SERIAL" > "$G/strings/0x409/serialnumber" ||
    fail serial-write-failed

echo SAMSUNG > "$G/strings/0x409/manufacturer" ||
    fail manufacturer-write-failed

echo SM-J720F_TWRP > "$G/strings/0x409/product" ||
    fail product-name-write-failed

mkdir -p "$G/configs/c.1/strings/0x409" ||
    fail config-create-failed

echo "Conf 1" > "$G/configs/c.1/strings/0x409/configuration" ||
    fail configuration-write-failed

echo 0x3f > "$G/configs/c.1/MaxPower" ||
    fail maxpower-write-failed

mkdir -p "$G/functions/ffs.adb" ||
    fail ffs-create-failed

if [ ! -L "$G/configs/c.1/ffs.adb" ]; then
    ln -s "$G/functions/ffs.adb" \
        "$G/configs/c.1/ffs.adb" ||
        fail ffs-link-failed
fi

mark configfs-ready

# Restart donor-era adbd only after ffs.adb exists.
setprop sys.usb.ffs.ready 0
setprop ctl.restart adbd
mark adbd-restarted

ATTEMPT=0

while [ "$ATTEMPT" -lt 15 ]; do
    if [ "$(getprop sys.usb.ffs.ready)" = "1" ]; then
        mark ffs-ready

        if echo 13600000.dwc3 > "$G/UDC"; then
            setprop sys.usb.state adb
            mark bound
            exit 0
        fi

        fail bind-failed
    fi

    sleep 1
    ATTEMPT=$((ATTEMPT + 1))
done

fail ffs-timeout
