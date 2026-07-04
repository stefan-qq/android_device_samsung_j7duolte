# Copyright (C) 2026 The Android Open Source Project
# Copyright (C) 2026 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

DEVICE_PATH := device/samsung/j7duolte

# For building with minimal manifest
ALLOW_MISSING_DEPENDENCIES := true

# -----------------------------------------------------------------------------
# Architecture - Capped at 32-bit to reduce pointer sizes and binary tables
# -----------------------------------------------------------------------------
TARGET_ARCH := arm
TARGET_ARCH_VARIANT := armv7-a-neon
TARGET_CPU_ABI := armeabi-v7a
TARGET_CPU_ABI2 := armeabi
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := cortex-a53

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
# Kernel - Layout matched exactly to physical storage specs
# -----------------------------------------------------------------------------
BOARD_KERNEL_BASE := 0x10000000
BOARD_KERNEL_CMDLINE := androidboot.selinux=permissive
BOARD_KERNEL_PAGESIZE := 2048
BOARD_RAMDISK_OFFSET := 0x01000000
BOARD_KERNEL_TAGS_OFFSET := 0x00000100

BOARD_MKBOOTIMG_ARGS += --kernel_offset 0x00008000
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)

# -----------------------------------------------------------------------------
# Prebuilt Kernel Config (Raw uncompressed stock kernel)
# -----------------------------------------------------------------------------
TARGET_FORCE_PREBUILT_KERNEL := true

ifeq ($(TARGET_FORCE_PREBUILT_KERNEL),true)
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel
TARGET_PREBUILT_DT := $(DEVICE_PATH)/prebuilt/dt.img
BOARD_MKBOOTIMG_ARGS += --dtb $(TARGET_PREBUILT_DT)
BOARD_KERNEL_SEPARATED_DT := 
endif

# -----------------------------------------------------------------------------
# Partitions (Strict J7 Duo hardware boundary rules)
# -----------------------------------------------------------------------------
BOARD_FLASH_BLOCK_SIZE := 131072
BOARD_BOOTIMAGE_PARTITION_SIZE := 31848992
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 31848992 

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
# TWRP Exhaustive Feature Cuts (Android 10 Ramdisk Size Minimization)
# -----------------------------------------------------------------------------
TW_THEME := portrait_mdpi
TW_EXTRA_LANGUAGES := false

# Max out userland compression utilities
BOARD_RAMDISK_COMPRESSION := xz
LZMA_RAMDISK_TARGETS := recovery

# Core minimal compilation behaviors
TW_BUILD_MINIMAL_TWRP := true
TW_MINIMAL_BUILD := true
TW_DISABLE_TTF := true

# Drop heavy unnecessary binaries included by default in Android 10
TW_EXCLUDE_LPDUMP := true
TW_EXCLUDE_PYTHON := true
TW_EXCLUDE_SUPOL := true
TW_EXCLUDE_APEX := true

# Pure storage optimization cuts (Using explicit exclusion flags)
TW_EXCLUDE_MTP := true
TW_EXCLUDE_TZDATA := true
TW_EXCLUDE_NANO := true
TW_EXCLUDE_BASH := true
TW_EXCLUDE_FB2PNG := true
TW_EXCLUDE_TWRPAPP := true
TW_EXCLUDE_LOGCAT := true
TW_NO_EXFAT := true
TW_NO_EXFAT_FUSE := true
TW_EXCLUDE_RESETPROP := true
TW_EXCLUDE_ANYKERNEL := true
TW_EXCLUDE_ENCRYPTED_BACKUPS := true
TW_EXCLUDE_QUOTA := true
TW_EXCLUDE_SYSLOG := true

TW_SCREEN_BLANK_ON_BOOT := true
TW_INPUT_BLACKLIST := "hbtp_vm"
TW_USE_TOOLBOX := true
