#!/sbin/sh

PATH=/sbin:/system/bin
export PATH

REPORT=/tmp/J720F_RC23_RUNTIME.txt
SD_REPORT=/external_sd/J720F_RC23_RUNTIME.txt

capture_state() {
    LABEL="$1"
    {
        echo
        echo "=== $LABEL ==="
        echo "date=$(/sbin/date 2>&1)"
        echo "getenforce=$(/sbin/getenforce 2>&1)"
        echo "recovery=$(/sbin/getprop init.svc.recovery)"
        echo "adbd=$(/sbin/getprop init.svc.adbd)"
        echo "ffs_ready=$(/sbin/getprop sys.usb.ffs.ready)"
        echo "usb_config=$(/sbin/getprop sys.usb.config)"
        echo "usb_state=$(/sbin/getprop sys.usb.state)"
        echo "usb_controller=$(/sbin/getprop sys.usb.controller)"
        echo
        echo '-- J720F USB ACTION MARKERS --'
        /sbin/getprop 2>&1 | /sbin/grep 'j720f.usb'
        echo
        echo '-- MOUNTS --'
        /sbin/cat /proc/mounts 2>&1
        echo
        echo '-- FILESYSTEMS --'
        /sbin/cat /proc/filesystems 2>&1
        echo
        echo '-- FUNCTIONFS --'
        /sbin/ls -laZ /dev/usb-ffs /dev/usb-ffs/adb 2>&1
        for F in /dev/usb-ffs/adb/ep0 /dev/usb-ffs/adb/ep1 /dev/usb-ffs/adb/ep2; do
            echo "--- $F"
            /sbin/ls -lZ "$F" 2>&1
        done
        echo
        echo '-- CONFIGFS --'
        /sbin/ls -ldZ /sys/kernel/config 2>&1
        /sbin/ls -laZ /sys/kernel/config 2>&1
        /sbin/ls -laZ /sys/kernel/config/usb_gadget 2>&1
        /sbin/find /sys/kernel/config/usb_gadget/g1 -maxdepth 5 -print 2>&1
        for F in \
            /sys/kernel/config/usb_gadget/g1/UDC \
            /sys/kernel/config/usb_gadget/g1/idVendor \
            /sys/kernel/config/usb_gadget/g1/idProduct; do
            echo "--- $F"
            /sbin/cat "$F" 2>&1
        done
        echo
        echo '-- UDC --'
        /sbin/ls -laZ /sys/class/udc 2>&1
        for F in /sys/class/udc/*/state; do
            echo "--- $F"
            /sbin/cat "$F" 2>&1
        done
        echo
        echo '-- SAMSUNG ANDROID_USB --'
        /sbin/ls -laZ /sys/class/android_usb/android0 2>&1
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
        echo '-- TMP AND FIFO STATE --'
        /sbin/ls -ldZ /tmp /sbin 2>&1
        /sbin/ls -laZ /tmp 2>&1
        echo
        echo '-- PROCESSES --'
        /sbin/ps 2>&1
        echo
        echo '-- DMESG USB/SELINUX --'
        /sbin/dmesg 2>&1 | /sbin/grep -iE 'usb|dwc3|configfs|functionfs|ffs|adbd|android_usb|avc|denied|selinux|twadbfifo|orsin|terminal'
    } >> "$REPORT"
}

{
    echo '=== J720F RC2.3 RUNTIME DIAGNOSTICS ==='
    echo 'purpose=identify FunctionFS, ConfigFS, SELinux FIFO and terminal failures'
} > "$REPORT"

# Give TWRP and its post-boot hook a moment to settle before the first snapshot.
/sbin/sleep 5
capture_state PRE_RETRY

{
    echo
    echo '=== FIFO CREATE TEST ==='
    /sbin/rm -f /tmp/j720f_rc23_fifo_test
    /sbin/mkfifo /tmp/j720f_rc23_fifo_test 2>&1
    echo "mkfifo_tmp_rc=$?"
    /sbin/ls -lZ /tmp/j720f_rc23_fifo_test 2>&1
    /sbin/rm -f /tmp/j720f_rc23_fifo_test

    echo
    echo '=== FUNCTIONFS MOUNT RETRY ==='
    if /sbin/grep -q ' /dev/usb-ffs/adb ' /proc/mounts 2>/dev/null; then
        echo 'functionfs_already_mounted=1'
    else
        /sbin/mount -t functionfs -o uid=2000,gid=2000 adb /dev/usb-ffs/adb 2>&1
        echo "functionfs_mount_rc=$?"
    fi

    echo
    echo '=== CONFIGFS MOUNT RETRY ==='
    if /sbin/grep -q ' /sys/kernel/config ' /proc/mounts 2>/dev/null; then
        echo 'configfs_already_mounted=1'
    else
        /sbin/mount -t configfs none /sys/kernel/config 2>&1
        echo "configfs_mount_rc=$?"
    fi

    echo
    echo '=== ADBD RESTART AFTER MOUNT RETRY ==='
    /sbin/setprop ctl.stop adbd
    /sbin/sleep 1
    /sbin/setprop sys.usb.ffs.ready 0
    /sbin/setprop ctl.start adbd
    /sbin/sleep 8
} >> "$REPORT" 2>&1

capture_state POST_RETRY

{
    echo
    echo '=== DATA READ-ONLY PROBE ==='
    /sbin/blkid /dev/block/mmcblk0p28 2>&1
    /sbin/tune2fs -l /dev/block/mmcblk0p28 2>&1 | /sbin/head -80
    echo
    echo '=== END ==='
} >> "$REPORT"

# Mount and copy only after the report is complete. Failure remains in /tmp.
if ! /sbin/grep -q ' /external_sd ' /proc/mounts 2>/dev/null; then
    /sbin/twrp mount /external_sd >> "$REPORT" 2>&1
fi
if /sbin/grep -q ' /external_sd ' /proc/mounts 2>/dev/null; then
    /sbin/cp "$REPORT" "$SD_REPORT" 2>> "$REPORT"
    /sbin/sync
fi

exit 0
