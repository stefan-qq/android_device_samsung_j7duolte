# Samsung Galaxy J7 Duo (SM-J720F) - donor-era TWRP 3.3 product

$(call inherit-product, $(SRC_TARGET_DIR)/product/aosp_base_telephony.mk)
$(call inherit-product, vendor/omni/config/common.mk)

PRODUCT_DEVICE := j7duolte
PRODUCT_NAME := omni_j7duolte
PRODUCT_MODEL := SM-J720F
PRODUCT_BRAND := samsung
PRODUCT_MANUFACTURER := samsung

PRODUCT_DEFAULT_PROPERTY_OVERRIDES += \
    ro.secure=0 \
    ro.adb.secure=0 \
    ro.debuggable=1 \
    persist.sys.usb.config=adb
