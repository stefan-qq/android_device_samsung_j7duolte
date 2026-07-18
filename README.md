# Samsung Galaxy J7 Duo (SM-J720F) — TWRP 3.3 bring-up

This branch uses the Android 7.1 donor-era TWRP 3.3 userspace that produced the
proven v11 display and touch result, together with the exact J720F Android 10
stock kernel and device tree.

Current release-candidate goals:

- working UI and touch;
- writable FAT32 microSD at `/external_sd`;
- EFS/CPEFS raw-image backup without mounting them;
- ADB-only ConfigFS USB using the stock controller `13600000.dwc3`;
- no MTP during bring-up;
- legacy footer-based `/data` decryption only. Android 10 FBE/system-vold mixing
  is deliberately disabled.

Existing encrypted `/data` is not promised to decrypt. Do not format `/data`
unless its contents may be destroyed and a tested recovery image is available.

Build only with `.github/workflows/TWRP-3.3-J720F.yml` from the paired builder
repository.
