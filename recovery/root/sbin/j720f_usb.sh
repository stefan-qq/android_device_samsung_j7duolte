#!/sbin/sh

exec > /tmp/j720f-usb.log 2>&1
set -x

# Leave TWRP's initial partition and uevent setup undisturbed.
sleep 10

G=/sys/kernel/config/usb_gadget/g1

mkdir -p /sys/kernel/config
mount -t configfs none /sys/kernel/config 2>/dev/null || true

# Disable the inactive legacy gadget before switching to ConfigFS.
if [ -e /sys/class/android_usb/android0/enable ]; then
    echo 0 > /sys/class/android_usb/android0/enable 2>/dev/null || true
fi

mkdir -p "$G"
echo 0x04e8 > "$G/idVendor" || exit 1
echo 0x6860 > "$G/idProduct" || exit 1
echo 0x0404 > "$G/bcdDevice" || exit 1
echo 0x0200 > "$G/bcdUSB" || exit 1

mkdir -p "$G/strings/0x409"

SERIAL="$(getprop ro.serialno)"
[ -n "$SERIAL" ] || SERIAL=0123456789ABCDEF

echo "$SERIAL" > "$G/strings/0x409/serialnumber" || exit 1
echo SAMSUNG > "$G/strings/0x409/manufacturer" || exit 1
echo SM-J720F_TWRP > "$G/strings/0x409/product" || exit 1

mkdir -p "$G/configs/c.1/strings/0x409"
echo ADB > "$G/configs/c.1/strings/0x409/configuration" || exit 1
echo 0x3f > "$G/configs/c.1/MaxPower" || exit 1

mkdir -p "$G/functions/ffs.adb"

if [ ! -L "$G/configs/c.1/ffs.adb" ]; then
    ln -s "$G/functions/ffs.adb" "$G/configs/c.1/ffs.adb" || exit 1
fi

setprop sys.usb.j720f.configured 1

# init restarts adbd after configured becomes 1. Bind only after adbd has
# opened the FunctionFS endpoints.
attempt=0
while [ "$attempt" -lt 20 ]; do
    if [ "$(getprop sys.usb.ffs.ready)" = "1" ]; then
        echo 13600000.dwc3 > "$G/UDC" || exit 1
        setprop sys.usb.state adb
        setprop sys.usb.j720f.bound 1
        exit 0
    fi

    sleep 1
    attempt=$((attempt + 1))
done

setprop sys.usb.j720f.bound 0
exit 1
