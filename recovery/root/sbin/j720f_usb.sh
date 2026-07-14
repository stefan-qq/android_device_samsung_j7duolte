#!/sbin/sh

exec > /tmp/j720f-usb.log 2>&1
set -x

G=/sys/kernel/config/usb_gadget/g1

setprop sys.usb.j720f.stage setup

if [ -e /sys/class/android_usb/android0/enable ]; then
    echo 0 > /sys/class/android_usb/android0/enable 2>/dev/null || true
fi

mkdir -p /sys/kernel/config
mount -t configfs none /sys/kernel/config 2>/dev/null || true

mkdir -p "$G" || exit 1

if [ -e "$G/UDC" ]; then
    echo "" > "$G/UDC" 2>/dev/null || true
fi

echo 0x04e8 > "$G/idVendor" || exit 1
echo 0x6860 > "$G/idProduct" || exit 1
echo 0x0404 > "$G/bcdDevice" || exit 1
echo 0x0200 > "$G/bcdUSB" || exit 1

mkdir -p "$G/strings/0x409" || exit 1

SERIAL="$(getprop ro.serialno)"
[ -n "$SERIAL" ] || SERIAL=0123456789ABCDEF

echo "$SERIAL" > "$G/strings/0x409/serialnumber" || exit 1
echo SAMSUNG > "$G/strings/0x409/manufacturer" || exit 1

mkdir -p "$G/configs/c.1/strings/0x409" || exit 1
echo ADB > "$G/configs/c.1/strings/0x409/configuration" || exit 1
echo 0x3f > "$G/configs/c.1/MaxPower" || exit 1

mkdir -p "$G/functions/ffs.adb" || exit 1

if [ ! -L "$G/configs/c.1/ffs.adb" ]; then
    ln -s "$G/functions/ffs.adb" \
        "$G/configs/c.1/ffs.adb" || exit 1
fi

setprop sys.usb.j720f.stage waiting_ffs

READY=0
ATTEMPT=0

while [ "$ATTEMPT" -lt 5 ]; do
    if [ "$(getprop sys.usb.ffs.ready)" = "1" ]; then
        READY=1
        break
    fi

    sleep 1
    ATTEMPT=$((ATTEMPT + 1))
done

if [ "$READY" = "1" ]; then
    echo SM-J720F_TWRP_ADB_READY \
        > "$G/strings/0x409/product" || exit 1
    STAGE=bound_ready
else
    echo SM-J720F_TWRP_ADB_FORCED \
        > "$G/strings/0x409/product" || exit 1
    STAGE=bound_forced
fi

if ! echo 13600000.dwc3 > "$G/UDC"; then
    setprop sys.usb.j720f.stage bind_failed
    exit 1
fi

setprop sys.usb.state adb
setprop sys.usb.j720f.stage "$STAGE"
exit 0
