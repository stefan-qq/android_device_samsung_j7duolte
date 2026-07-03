# Copyright (C) 2026 The Android Open Source Project
# Copyright (C) 2026 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

DEVICE_PATH := device/samsung/j7duolte

# For building with minimal manifest
ALLOW_MISSING_DEPENDENCIES := true

# -----------------------------------------------------------------------------
# Architecture
# -----------------------------------------------------------------------------

TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := generic

TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv7-a-neon
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic
TARGET_2ND_CPU_VARIANT_RUNTIME := cortex-a53

# -----------------------------------------------------------------------------
# APEX
# -----------------------------------------------------------------------------

OVERRIDE_TARGET_FLATTEN_APEX := true

# -----------------------------------------------------------------------------
# Bootloader
# -----------------------------------------------------------------------------

TARGET_BOOTLOADER_BOARD_NAME := exynos7884
TARGET_NO_BOOTLOADER := true

# -----------------------------------------------------------------------------
# Display
# -----------------------------------------------------------------------------

TARGET_SCREEN_DENSITY := 280

# -----------------------------------------------------------------------------
# Compress stock kernel if necessary
# -----------------------------------------------------------------------------

$(shell if od -An -N2 -t x1 $(DEVICE_PATH)/prebuilt/kernel | grep -q '1f 8b'; then \
cp $(DEVICE_PATH)/prebuilt/kernel $(DEVICE_PATH)/prebuilt/kernel.gz; \
else \
gzip -9 -c $(DEVICE_PATH)/prebuilt/kernel > $(DEVICE_PATH)/prebuilt/kernel.gz; \
fi)

# -----------------------------------------------------------------------------
# Kernel
# -----------------------------------------------------------------------------

BOARD_KERNEL_BASE := 0x10000000
BOARD_KERNEL_CMDLINE := androidboot.selinux=permissive
BOARD_KERNEL_PAGESIZE := 2048
BOARD_RAMDISK_OFFSET := 0x01000000
BOARD_KERNEL_TAGS_OFFSET := 0x00000100

BOARD_MKBOOTIMG_ARGS += --kernel_offset 0x00008000
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)
BOARD_MKBOOTIMG_ARGS += --header_version 0

BOARD_KERNEL_IMAGE_NAME := Image.gz

BOARD_KERNEL_SEPARATED_DT := true

TARGET_KERNEL_CONFIG := j7duolte_defconfig
TARGET_KERNEL_SOURCE := kernel/samsung/j7duolte

# -----------------------------------------------------------------------------
# Prebuilt kernel
# -----------------------------------------------------------------------------

TARGET_FORCE_PREBUILT_KERNEL := true

ifeq ($(TARGET_FORCE_PREBUILT_KERNEL),true)

TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel.gz

TARGET_PREBUILT_DT := $(DEVICE_PATH)/prebuilt/dt.img

BOARD_MKBOOTIMG_ARGS += --dtb $(TARGET_PREBUILT_DT)

BOARD_KERNEL_SEPARATED_DT :=

endif

# -----------------------------------------------------------------------------
# Partitions
# -----------------------------------------------------------------------------

BOARD_FLASH_BLOCK_SIZE := 131072
BOARD_BOOTIMAGE_PARTITION_SIZE := 31848992
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 39845888

BOARD_HAS_LARGE_FILESYSTEM := true

BOARD_SYSTEMIMAGE_PARTITION_TYPE := ext4
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_USERDATAIMAGE_FILE_SYSTEM_TYPE := ext4

TARGET_COPY_OUT_VENDOR := vendor

# -----------------------------------------------------------------------------
# Platform
# -----------------------------------------------------------------------------

TARGET_BOARD_PLATFORM := universal7884

# -----------------------------------------------------------------------------
# Recovery
# -----------------------------------------------------------------------------

TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true

# -----------------------------------------------------------------------------
# TWRP
# -----------------------------------------------------------------------------

TW_THEME := portrait_mdpi
TW_EXTRA_LANGUAGES := false

LZMA_RAMDISK_TARGETS := recovery

TW_DISABLE_TTF := true
TW_EXCLUDE_MTP := true
TW_EXCLUDE_TZDATA := true
TW_EXCLUDE_NANO := true
TW_EXCLUDE_BASH := true
TW_EXCLUDE_APEX := true
TW_EXCLUDE_FB2PNG := true
TW_EXCLUDE_TWRPAPP := true
TW_EXCLUDE_LOGCAT := true
TW_NO_EXFAT := true
TW_NO_EXFAT_FUSE := true
TW_INCLUDE_CRYPTO_FBE := false
TW_EXCLUDE_RESETPROP := true
TW_EXCLUDE_ANYKERNEL := true

TW_SCREEN_BLANK_ON_BOOT := true
TW_INPUT_BLACKLIST := "hbtp_vm"
TW_USE_TOOLBOX := true
