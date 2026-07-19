#!/sbin/sh

PATH=/sbin:/system/bin
export PATH

REPORT=/tmp/J720F_RUNTIME_DIAGNOSTICS.txt
SD_REPORT=/external_sd/J720F_RUNTIME_DIAGNOSTICS.txt

# Write immediately so even a partial file proves that init launched the service.
{
    echo '=== J720F TWRP RUNTIME DIAGNOSTICS ==='
    echo 'service_started=1'
    echo "date=$(/sbin/date 2>&1)"
    echo "pid=$$"
} > "$REPORT" 2>&1

# Run independently after the UI has had time to finish startup.
/sbin/sleep 20

{
    echo
    echo '=== SELINUX ==='
    echo -n 'enforce='
    /sbin/cat /sys/fs/selinux/enforce 2>&1
    echo -n 'init_context='
    /sbin/cat /proc/1/attr/current 2>&1
    echo -n 'service_context='
    /sbin/cat /proc/self/attr/current 2>&1
    echo -n 'cmdline='
    /sbin/cat /proc/cmdline 2>&1

    echo
    echo '=== PROPERTIES ==='
    /sbin/getprop 2>&1

    echo
    echo '=== MOUNTS ==='
    /sbin/cat /proc/mounts 2>&1

    echo
    echo '=== FUNCTIONFS ==='
    /sbin/ls -ld /dev/usb-ffs /dev/usb-ffs/adb 2>&1
    /sbin/ls -la /dev/usb-ffs/adb 2>&1

    echo
    echo '=== CONFIGFS ==='
    /sbin/ls -ld /sys/kernel/config 2>&1
    /sbin/ls -la /sys/kernel/config/usb_gadget/g1 2>&1
    for F in \
        /sys/kernel/config/usb_gadget/g1/UDC \
        /sys/kernel/config/usb_gadget/g1/idVendor \
        /sys/kernel/config/usb_gadget/g1/idProduct; do
        echo "--- $F"
        /sbin/cat "$F" 2>&1
    done

    echo
    echo '=== UDC ==='
    /sbin/ls -la /sys/class/udc 2>&1
    for F in /sys/class/udc/*/state; do
        echo "--- $F"
        /sbin/cat "$F" 2>&1
    done

    echo
    echo '=== SAMSUNG ANDROID_USB ==='
    /sbin/ls -la /sys/class/android_usb/android0 2>&1
    for F in \
        /sys/class/android_usb/android0/enable \
        /sys/class/android_usb/android0/idVendor \
        /sys/class/android_usb/android0/idProduct \
        /sys/class/android_usb/android0/functions \
        /sys/class/android_usb/android0/f_ffs/aliases; do
        echo "--- $F"
        /sbin/cat "$F" 2>&1
    done

    echo
    echo '=== DATA HEADER (READ ONLY) ==='
    /sbin/blkid /dev/block/mmcblk0p28 2>&1
    /sbin/hexdump -C -n 4096 /dev/block/mmcblk0p28 2>&1 | /sbin/head -n 16

    echo
    echo '=== PROCESSES ==='
    /sbin/ps 2>&1

    echo
    echo '=== DMESG USB/SELINUX ==='
    /sbin/dmesg 2>&1 | /sbin/grep -iE \
        'usb|dwc3|configfs|functionfs|ffs|adbd|android_usb|avc|denied|selinux'

    echo
    echo '=== END ==='
} >> "$REPORT" 2>&1

# Never mount or invoke TWRP here. Copy only if TWRP already mounted the card.
if /sbin/grep -q ' /external_sd ' /proc/mounts 2>/dev/null; then
    /sbin/cp "$REPORT" "$SD_REPORT" 2>/dev/null
    /sbin/sync
fi

exit 0
