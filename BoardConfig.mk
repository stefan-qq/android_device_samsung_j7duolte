# Copyright (C) 2026 The Android Open Source Project
# SPDX-License-Identifier: Apache-2.0

DEVICE_PATH := device/samsung/j7duolte

# Build
ALLOW_MISSING_DEPENDENCIES := true

# Architecture
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
TARGET_2ND_CPU_VARIANT := cortex-a53
TARGET_2ND_CPU_VARIANT_RUNTIME := cortex-a53

# Platform / bootloader
TARGET_BOARD_PLATFORM := universal7884
TARGET_BOOTLOADER_BOARD_NAME := exynos7884
TARGET_NO_BOOTLOADER := true

# Stock J720F legacy boot-image geometry
BOARD_KERNEL_BASE := 0x10000000
BOARD_KERNEL_PAGESIZE := 2048
BOARD_KERNEL_CMDLINE := androidboot.selinux=permissive androidboot.selinux=permissive
BOARD_RAMDISK_OFFSET := 0x01000000
BOARD_SECOND_OFFSET := 0x00f00000
BOARD_KERNEL_TAGS_OFFSET := 0x00000100
BOARD_KERNEL_IMAGE_NAME := Image
BOARD_KERNEL_BOARD_NAME := SRPRA09A005RU

BOARD_MKBOOTIMG_ARGS += --kernel_offset 0x00008000
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --second_offset $(BOARD_SECOND_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)
BOARD_MKBOOTIMG_ARGS += --board $(BOARD_KERNEL_BOARD_NAME)

# Keep the exact Android 10 stock kernel and DT for the first source build.
TARGET_FORCE_PREBUILT_KERNEL := true
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel

# Do not ask the legacy build system to regenerate dt.img with dtbToolCM.
# Package the exact stock DT payload directly into the recovery image.
BOARD_MKBOOTIMG_ARGS += --dt $(DEVICE_PATH)/prebuilt/dt.img

BOARD_BUILD_SYSTEM_ROOT_IMAGE := false

# Partitions (PIT-derived, 512-byte sectors)
BOARD_FLASH_BLOCK_SIZE := 131072
BOARD_BOOTIMAGE_PARTITION_SIZE := 33554432
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 39845888
BOARD_SYSTEMIMAGE_PARTITION_SIZE := 4194304000
BOARD_VENDORIMAGE_PARTITION_SIZE := 528482304
BOARD_ODMIMAGE_PARTITION_SIZE := 419430400
BOARD_CACHEIMAGE_PARTITION_SIZE := 314572800

BOARD_HAS_LARGE_FILESYSTEM := true
BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_ODMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_USERDATAIMAGE_FILE_SYSTEM_TYPE := ext4
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := false
TARGET_COPY_OUT_VENDOR := vendor
TARGET_COPY_OUT_ODM := odm

# Recovery
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery.fstab
TARGET_SCREEN_DENSITY := 280
TW_THEME := portrait_mdpi

# First bring-up: ADB only. MTP and external SD deliberately stay disabled until
# USB enumeration and adbd are stable.
TW_EXCLUDE_MTP := true
BOARD_HAS_NO_REAL_SDCARD := true
RECOVERY_SDCARD_ON_DATA := true

# Android 10 stock userdata is legacy FDE with a crypto footer.
TW_INCLUDE_CRYPTO := true

# Keep the first image small and deterministic.
TW_EXCLUDE_TWRPAPP := true
TW_EXCLUDE_SUPERSU := true
