# Samsung Galaxy J7 Duo (SM-J720F) - donor-era TWRP 3.3 configuration

DEVICE_PATH := device/samsung/j7duolte

# The Android 7.1 recovery userspace is the only architecture proven to draw
# the UI and accept touch with the exact J720F Android 10 stock kernel and DT.
BOARD_VENDOR := samsung
TARGET_BOARD_PLATFORM := exynos5
TARGET_SOC := exynos7884
TARGET_BOOTLOADER_BOARD_NAME := exynos7884
TARGET_NO_BOOTLOADER := true
TARGET_NO_RADIOIMAGE := true

# Architecture
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := cortex-a53

TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv7-a-neon
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := cortex-a53

# Exact J720F Android 10 stock recovery payload and legacy header geometry
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel
BOARD_KERNEL_BASE := 0x10000000
BOARD_KERNEL_PAGESIZE := 2048
BOARD_KERNEL_CMDLINE := androidboot.selinux=permissive enforcing=0
BOARD_MKBOOTIMG_ARGS := --kernel_offset 0x00008000 \
    --ramdisk_offset 0x01000000 \
    --second_offset 0x00f00000 \
    --tags_offset 0x00000100 \
    --board SRPRA09A005RU \
    --dt $(DEVICE_PATH)/prebuilt/dt.img

# PIT-derived limits
BOARD_FLASH_BLOCK_SIZE := 131072
BOARD_BOOTIMAGE_PARTITION_SIZE := 33554432
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 39845888
BOARD_SYSTEMIMAGE_PARTITION_SIZE := 4194304000
BOARD_VENDORIMAGE_PARTITION_SIZE := 528482304
BOARD_ODMIMAGE_PARTITION_SIZE := 419430400
BOARD_CACHEIMAGE_PARTITION_SIZE := 314572800

# Filesystems
BOARD_HAS_LARGE_FILESYSTEM := true
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := false
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery.fstab

# Device-specific recovery SELinux policy
BOARD_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy

# TWRP 3.3 configuration from the exact UI-working v11 generation
RECOVERY_VARIANT := twrp
TW_THEME := portrait_hdpi
TARGET_SCREEN_DENSITY := 320
TARGET_RECOVERY_PIXEL_FORMAT := "ABGR_8888"
RECOVERY_GRAPHICS_USE_LINELENGTH := true
TW_BRIGHTNESS_PATH := "/sys/devices/14800000.dsim/backlight/panel/brightness"
TW_MAX_BRIGHTNESS := 255
TW_DEFAULT_BRIGHTNESS := 150
TW_NO_REBOOT_BOOTLOADER := true
TW_HAS_DOWNLOAD_MODE := true
TW_USE_NEW_MINADBD := true
TW_EXTRA_LANGUAGES := true

# Keep legacy footer-based FDE support. Do not mix Android 7.1 recovery with
# Android 10 FBE or system-vold integration; those paths were not functional.
TW_INCLUDE_CRYPTO := true

# /data/media remains the internal-storage model; the device also has a real
# removable microSD. Prefer that working card while stock-encrypted /data is
# unavailable in the Android 7.1 recovery userspace.
BOARD_HAS_NO_REAL_SDCARD := true
RECOVERY_SDCARD_ON_DATA := true
TW_DEFAULT_EXTERNAL_STORAGE := true

# MTP is disabled until USB ADB is proven stable. This also removes the noisy
# "Unknown MTP message type" path from partition updates.
TW_EXCLUDE_MTP := true
TW_EXCLUDE_TWRPAPP := true
TW_EXCLUDE_SUPERSU := true
