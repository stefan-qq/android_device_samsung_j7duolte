# Copyright (C) 2026 The Android Open Source Project
# SPDX-License-Identifier: Apache-2.0

$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base.mk)
$(call inherit-product, vendor/omni/config/common.mk)
$(call inherit-product, device/samsung/j7duolte/device.mk)

PRODUCT_DEVICE := j7duolte
PRODUCT_NAME := omni_j7duolte
PRODUCT_BRAND := samsung
PRODUCT_MODEL := SM-J720F
PRODUCT_MANUFACTURER := samsung
PRODUCT_SHIPPING_API_LEVEL := 26

PRODUCT_BUILD_PROP_OVERRIDES += \
    PRIVATE_BUILD_DESC="j7duoltedd-user 10 QP1A.190711.020 J720FDDS7CUL1 release-keys"

BUILD_FINGERPRINT := samsung/j7duoltedd/j7duolte:10/QP1A.190711.020/J720FDDS7CUL1:user/release-keys
