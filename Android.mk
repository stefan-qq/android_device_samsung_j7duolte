LOCAL_PATH := $(call my-dir)

ifeq ($(TARGET_DEVICE),j7duolte)
include $(call all-makefiles-under,$(LOCAL_PATH))
endif
