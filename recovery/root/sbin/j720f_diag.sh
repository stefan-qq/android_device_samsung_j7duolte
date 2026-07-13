#!/sbin/sh

PATH=/sbin:/system/bin
export PATH

TMP_LOG=/tmp/j720f-adb-first.log
CACHE_DEV=/dev/block/platform/13500000.dwmmc0/by-name/CACHE
CACHE_DIR=/cache/recovery
CACHE_LOG=${CACHE_DIR}/j720f-adb-first.log

exec >"${TMP_LOG}" 2>&1

echo "=== J720F ADB-first recovery diagnostic ==="
date
echo "pid=$$"
echo "context=$(cat /proc/self/attr/current 2>/dev/null)"
echo "cmdline=$(cat /proc/cmdline 2>/dev/null)"
echo "<6>J720F_DIAG: service started" > /dev/kmsg 2>/dev/null

echo "--- SELinux ---"
getenforce 2>/dev/null
setenforce 0 2>/dev/null
echo "setenforce_rc=$?"
getenforce 2>/dev/null

# ueventd may need a moment to create the PIT-backed by-name links.
i=0
while [ ! -e "${CACHE_DEV}" ] && [ "${i}" -lt 20 ]; do
    sleep 1
    i=$((i + 1))
done

echo "--- cache setup ---"
ls -l "${CACHE_DEV}" 2>&1
mkdir -p /cache
if ! grep -q ' /cache ' /proc/mounts; then
    mount -t ext4 -o rw,noatime "${CACHE_DEV}" /cache
    echo "cache_mount_rc=$?"
fi
grep ' /cache ' /proc/mounts || true

if grep -q ' /cache ' /proc/mounts; then
    mkdir -p "${CACHE_DIR}"
    cp "${TMP_LOG}" "${CACHE_LOG}"
    exec >>"${CACHE_LOG}" 2>&1
    echo "persistent_log=${CACHE_LOG}"
else
    echo "persistent cache log unavailable; retaining ${TMP_LOG}"
fi

snapshot() {
    label="$1"
    echo
    echo "=== snapshot ${label} ==="
    date

    echo "--- selected properties ---"
    getprop | grep -E 'ro.hardware|ro.boot.hardware|ro.serialno|ro.secure|ro.adb.secure|ro.debuggable|sys.usb|persist.sys.usb|service.adb' || true

    echo "--- processes ---"
    ps -A 2>&1
    adbd_pid="$(pidof adbd 2>/dev/null)"
    echo "adbd_pid=${adbd_pid}"
    if [ -n "${adbd_pid}" ]; then
        cat "/proc/${adbd_pid}/status" 2>/dev/null
        echo -n "adbd_context="
        cat "/proc/${adbd_pid}/attr/current" 2>/dev/null
    fi

    echo "--- mounts relevant to USB/cache ---"
    grep -E ' /cache | /sys/kernel/config | /dev/usb-ffs/adb ' /proc/mounts || true

    echo "--- UDC ---"
    ls -la /sys/class/udc 2>&1
    for node in /sys/class/udc/*; do
        [ -e "${node}" ] || continue
        echo "UDC=${node}"
        cat "${node}/state" 2>/dev/null
        cat "${node}/current_speed" 2>/dev/null
    done

    echo "--- ConfigFS gadget ---"
    find /sys/kernel/config/usb_gadget/g1 -maxdepth 6 -print 2>&1
    echo -n "g1_UDC="
    cat /sys/kernel/config/usb_gadget/g1/UDC 2>/dev/null

    echo "--- FunctionFS endpoints ---"
    ls -la /dev/usb-ffs /dev/usb-ffs/adb 2>&1

    echo "--- display nodes, without starting recovery ---"
    ls -la /dev/graphics /dev/fb* /sys/class/graphics /sys/class/backlight 2>&1
    find /sys/class/backlight -maxdepth 2 -type f -print 2>&1

    echo "--- recent kernel/init messages ---"
    dmesg | tail -n 250
}

snapshot boot

i=5
while [ "${i}" -le 30 ]; do
    sleep 5
    snapshot "${i}s"
    i=$((i + 5))
done

echo "--- pstore present at diagnostic completion ---"
if [ -d /sys/fs/pstore ]; then
    find /sys/fs/pstore -maxdepth 2 -print 2>&1
    if grep -q ' /cache ' /proc/mounts; then
        mkdir -p "${CACHE_DIR}/j720f-pstore"
        cp -a /sys/fs/pstore/. "${CACHE_DIR}/j720f-pstore/" 2>/dev/null || true
    fi
fi

echo "<6>J720F_DIAG: snapshots complete" > /dev/kmsg 2>/dev/null
sync

# Android bugreports commonly include /cache/recovery/last_log. Preserve the
# previous file once, then publish this diagnostic log there as well.
if grep -q ' /cache ' /proc/mounts; then
    if [ -f "${CACHE_DIR}/last_log" ] && [ ! -f "${CACHE_DIR}/last_log.before-j720f-diag" ]; then
        cp "${CACHE_DIR}/last_log" "${CACHE_DIR}/last_log.before-j720f-diag"
    fi
    cp "${CACHE_LOG}" "${CACHE_DIR}/last_log"
    sync
fi
