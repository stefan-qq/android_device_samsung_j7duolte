# Copyright (C) 2026 The Android Open Source Project
# SPDX-License-Identifier: Apache-2.0

# Files under recovery/root are copied by the recovery build itself. Do not add
# duplicate PRODUCT_COPY_FILES destinations for those files.

PRODUCT_PROPERTY_OVERRIDES += \
    ro.hardware=samsungexynos7885 \
    ro.product.board=exynos7884 \
    ro.board.platform=universal7884 \
    ro.product.device=j7duolte \
    ro.product.model=SM-J720F \
    ro.product.manufacturer=samsung \
    ro.secure=0 \
    ro.adb.secure=0 \
    ro.debuggable=1 \
    persist.sys.usb.config=adb
