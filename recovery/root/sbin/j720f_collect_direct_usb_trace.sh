#!/sbin/sh

PATH=/sbin:/system/bin
export PATH

MODE=${1:-manual}
OUTDIR=/external_sd/J720F_DIRECT_USB_TRACE

if ! /sbin/grep -q ' /external_sd ' /proc/mounts 2>/dev/null; then
    echo 'microSD is not mounted at /external_sd' >&2
    exit 1
fi

/sbin/mkdir -p "$OUTDIR" || exit 1

{
    echo '=== J720F DIRECT USB TRACE COLLECTION ==='
    echo "mode=$MODE"
    echo "date=$(/sbin/date 2>&1)"
    echo "collector_pid=$$"
    echo "recovery_context=$(/sbin/cat /proc/self/attr/current 2>&1)"
    echo "usb_config=$(/sbin/getprop sys.usb.config 2>&1)"
    echo "ffs_ready=$(/sbin/getprop sys.usb.ffs.ready 2>&1)"
    echo "adbd_state=$(/sbin/getprop init.svc.adbd 2>&1)"
    echo "udc=$(/sbin/cat /sys/kernel/config/usb_gadget/g1/UDC 2>&1)"
} > "$OUTDIR/collection_summary.txt" 2>&1

for FILE in \
    /tmp/J720F_ADBD_USB_TRACE.txt \
    /tmp/J720F_ADBD_TRACE.txt \
    /tmp/J720F_RUNTIME_DIAGNOSTICS.txt \
    /tmp/recovery.log; do
    if [ -f "$FILE" ]; then
        /sbin/cp "$FILE" "$OUTDIR/$(/sbin/basename "$FILE")" 2>/dev/null
    fi
done

/sbin/dmesg > "$OUTDIR/dmesg.txt" 2>&1
/sbin/getprop > "$OUTDIR/getprop.txt" 2>&1
/sbin/cat /proc/mounts > "$OUTDIR/mounts.txt" 2>&1
/sbin/ls -la /dev/usb-ffs/adb > "$OUTDIR/functionfs_endpoints.txt" 2>&1

{
    echo '=== CONFIGFS GADGET ==='
    /sbin/ls -la /sys/kernel/config/usb_gadget/g1 2>&1
    echo
    echo '=== FUNCTIONS ==='
    /sbin/ls -la /sys/kernel/config/usb_gadget/g1/functions 2>&1
    echo
    echo '=== CONFIG C.1 ==='
    /sbin/ls -la /sys/kernel/config/usb_gadget/g1/configs/c.1 2>&1
    echo
    for FILE in \
        /sys/kernel/config/usb_gadget/g1/UDC \
        /sys/kernel/config/usb_gadget/g1/idVendor \
        /sys/kernel/config/usb_gadget/g1/idProduct \
        /sys/class/udc/*/state; do
        echo "--- $FILE"
        /sbin/cat "$FILE" 2>&1
    done
} > "$OUTDIR/gadget_state.txt" 2>&1

{
    echo '=== TRACE FILE METADATA ==='
    /sbin/ls -lZ \
        /tmp/J720F_ADBD_USB_TRACE.txt \
        /tmp/J720F_ADBD_TRACE.txt \
        2>&1
    echo
    echo '=== TRACE MARKER COUNTS ==='
    echo -n 'direct_trace_lines='
    /sbin/grep -c 'J720F_USB_DIAG' /tmp/J720F_ADBD_USB_TRACE.txt 2>/dev/null || true
    echo -n 'native_trace_lines='
    /sbin/wc -l < /tmp/J720F_ADBD_TRACE.txt 2>/dev/null || true
} > "$OUTDIR/trace_metadata.txt" 2>&1

/sbin/sync

echo "Created: $OUTDIR"
exit 0
