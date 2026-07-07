# Copyright (C) 2026 The Android Open Source Project
# SPDX-License-Identifier: Apache-2.0
DEVICE_PATH := device/samsung/j7duolte
# -----------------------------------------------------------------------------
# Build
# -----------------------------------------------------------------------------
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
# Platform
# -----------------------------------------------------------------------------
TARGET_BOARD_PLATFORM := universal7884
# -----------------------------------------------------------------------------
# Bootloader
# -----------------------------------------------------------------------------
TARGET_BOOTLOADER_BOARD_NAME := exynos7884
TARGET_NO_BOOTLOADER := true
# -----------------------------------------------------------------------------
# APEX
# -----------------------------------------------------------------------------
OVERRIDE_TARGET_FLATTEN_APEX := true
# -----------------------------------------------------------------------------
# Display
# -----------------------------------------------------------------------------
TARGET_SCREEN_DENSITY := 280
# -----------------------------------------------------------------------------
# Kernel
# -----------------------------------------------------------------------------
BOARD_KERNEL_BASE := 0x10000000
BOARD_KERNEL_CMDLINE := androidboot.selinux=permissive
BOARD_KERNEL_PAGESIZE := 2048
BOARD_RAMDISK_OFFSET := 0x01000000
BOARD_KERNEL_TAGS_OFFSET := 0x00000100
BOARD_KERNEL_IMAGE_NAME := Image
BOARD_MKBOOTIMG_ARGS += --kernel_offset 0x00008000
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)
TARGET_KERNEL_SOURCE := kernel/samsung/j7duolte
TARGET_KERNEL_CONFIG := j7duolte_defconfig
TARGET_FORCE_PREBUILT_KERNEL := true
ifeq ($(TARGET_FORCE_PREBUILT_KERNEL),true)
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel
TARGET_PREBUILT_DT := $(DEVICE_PATH)/prebuilt/dt.img
BOARD_KERNEL_SEPARATED_DT := true
endif
BOARD_BUILD_SYSTEM_ROOT_IMAGE := false
# -----------------------------------------------------------------------------
# Recovery ramdisk (prebuilt — see notes below)
# -----------------------------------------------------------------------------
# This device's kernel does not successfully boot a ramdisk built from the
# twrp-11 minimal manifest's compiled init/recovery userspace (system-as-root
# style). A verified-working ramdisk was assembled using this device's own
# kernel+DTB paired with the classic-layout init/sbin/recovery userspace from
# a proven-working TWRP 3.3.0 build for a sibling Exynos device (j7y17lte),
# plus this device's own recovery.fstab. Using that prebuilt ramdisk directly
# rather than building one from source.
BOARD_PREBUILT_RECOVERY_RAMDISK := $(DEVICE_PATH)/prebuilt/ramdisk-recovery.cpio.gz
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
# Recovery
# -----------------------------------------------------------------------------
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true
