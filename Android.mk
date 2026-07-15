LOCAL_PATH := $(call my-dir)

ifeq ($(TARGET_DEVICE),j7duolte)
include $(LOCAL_PATH)/recovery/j720f_configfs_mount/Android.mk
endif
