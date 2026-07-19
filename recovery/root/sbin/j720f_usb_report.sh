#!/sbin/sh

PATH=/sbin:/system/bin
REPORT_TMP=/tmp/J720F_RC2_USB_REPORT.txt
REPORT_SD=/external_sd/J720F_RC2_USB_REPORT.txt

WAIT=0
while [ "$WAIT" -lt 90 ]; do
    if /sbin/grep -q ' /external_sd ' /proc/mounts 2>/dev/null; then
        break
    fi
    /sbin/sleep 1
    WAIT=$((WAIT + 1))
done

{
    echo '=== J720F RC2 USB REPORT ==='
    echo "wait_seconds=$WAIT"
    echo
    echo '=== PROPERTIES ==='
    /sbin/getprop 2>&1
    echo
    echo '=== MOUNTS ==='
    /sbin/cat /proc/mounts 2>&1
    echo
    echo '=== FILESYSTEMS ==='
    /sbin/cat /proc/filesystems 2>&1
    echo
    echo '=== UDC ==='
    /sbin/ls -la /sys/class/udc 2>&1
    for F in /sys/class/udc/*/state; do
        echo "--- $F"
        /sbin/cat "$F" 2>&1
    done
    echo
    echo '=== CONFIGFS ==='
    /sbin/ls -la /config 2>&1
    /sbin/ls -la /config/usb_gadget 2>&1
    /sbin/ls -la /config/usb_gadget/g1 2>&1
    /sbin/find /config/usb_gadget/g1 -maxdepth 5 -print 2>&1
    for F in \
        /config/usb_gadget/g1/UDC \
        /config/usb_gadget/g1/idVendor \
        /config/usb_gadget/g1/idProduct; do
        echo "--- $F"
        /sbin/cat "$F" 2>&1
    done
    echo
    echo '=== FUNCTIONFS ==='
    /sbin/ls -la /dev/usb-ffs /dev/usb-ffs/adb 2>&1
    echo
    echo '=== LEGACY ANDROID_USB ==='
    /sbin/ls -la /sys/class/android_usb/android0 2>&1
    for F in \
        /sys/class/android_usb/android0/enable \
        /sys/class/android_usb/android0/functions; do
        echo "--- $F"
        /sbin/cat "$F" 2>&1
    done
    echo
    echo '=== PROCESSES ==='
    /sbin/ps 2>&1
    echo
    echo '=== DMESG FILTERED ==='
    /sbin/dmesg 2>&1 | /sbin/grep -iE 'usb|dwc3|configfs|functionfs|ffs|adbd|avc|denied|selinux'
    echo
    echo '=== END ==='
} > "$REPORT_TMP"

if /sbin/grep -q ' /external_sd ' /proc/mounts 2>/dev/null; then
    /sbin/cp "$REPORT_TMP" "$REPORT_SD" 2>/dev/null
    /sbin/sync
fi

exit 0
