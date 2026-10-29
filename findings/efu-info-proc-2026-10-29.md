# ripdrv EFU `/proc/efu/info` and corrections to the 2026-10-29 kernel review (offline)

## Scope and build caveat (VERIFIED)

- Module: `tools/secr/ripdrv.arm.3.4.11-rt19.ko`, `.modinfo` `vermagic=3.4.11-rt19 SMP preempt mod_unload ARMv7`.
- The 23.1.b device is Linux 4.19.235 on aarch64 per [f1-gpl-source-request-2026-10-29.md](f1-gpl-source-request-2026-10-29.md) (boot log L818).
- **So this module is not from the 23.1.b kernel.** Every kernel-module finding in [f1-kernel-rip-keystore-decomp-2026-10-29.md](f1-kernel-rip-keystore-decomp-2026-10-29.md) describes this 3.4.11 build only. Applying them to 23.1.b is an assumption, not a result.

## Corrections to earlier notes

- **Callers of `rip_efu_proc_show` (corrected):** the earlier `bl fcn.080018d4` / `fcn.08001f90` / `fcn.08001fb8` calls from `rip_efu_proc_show` are not the real callees. In this relocatable `.ko`, the `bl` immediates are unresolved. The relocation table (`rizin ir`) names the real targets: `EFU_getSerialNumber` (0x080028fc), `EFU_getChipid` (0x08002924), `EFU_getOSIK` (0x08002944), `EFU_getBitmask` (0x08002978, 0x080029a0). Those earlier caller links are withdrawn.
- **`rip_proc_add_entry` callers:** no relocation names `rip_proc_add_entry`, so its `bl` immediates are intra-section and likely valid. The labels `fcn.080018d4` / `fcn.08001f90` / `fcn.08001fb8` still need a proper caller check before use.

## What the EFU info file does (VERIFIED on this build)

- `rip_efu_proc_init` (0x080029cc) creates the `efu` directory and, with `proc_create_data` mode `0x124` (octal `0444`, world-readable), the entry `info` (name string `info`, 0x08003f84). Other entries: `allowed` (mode 0x124), `allowed_bootloader` (0x124), `temporal_tag` (0x1a4).
- The `info` open routine is `rip_efu_info_proc_open` (0x080027bc, registered via ABS32 at 0x08003924), which calls `single_open` with `rip_efu_proc_show` (0x080028f0).
- `rip_efu_proc_show` prints:
  - `Serial: %s` (from `EFU_getSerialNumber`);
  - `ChipID: 0x%X` (from `EFU_getChipid`);
  - `Key   : %08X...` (format at 0x08003f20), from `EFU_getOSIK` into a 0x100-byte buffer, passing only the first 32-bit word (byte-swapped with `rev`);
  - `EFU BITMASK: %08x%08x` and the permanent and temporal tag state (from `EFU_getBitmask`).

**Result:** on this build, a local user can read the first 4 bytes of the `EFU_getOSIK` output from world-readable `/proc/efu/info`. That is a partial disclosure, not a full key.

## Not shown

- Whether the 23.1.b device has `/proc/efu/info` at all. The module is not the 23.1.b build.
- Whether OSIK is the same key as OSCK (item `0x121`). Nothing in the repo links them, and the 19.x trials used OSCK. Treat them as separate until shown otherwise.
- The byte values of the printed word. No live read was done.
- Whether `rip_proc_new` (0x080015b8, referenced by ABS32 at 0x08004210) can create item `0x121`. Its registration is a function pointer, and the caller path is not traced.

## EFU_getOSIK decoded (VERIFIED by disassembly and file comparison)

- `EFU_getOSIK` (0x08002198, 68 bytes) calls `rip2_drv_read(&len, 0x120, buf)`. Item `0x120` is **not** `0x121` (the OSCK item in `rip_proc_init`), so OSIK and OSCK are different items.
- If that read does not return 1, it `memcpy`s a 256-byte table from `0x080037f8` into the caller's buffer.
- `rip2_drv_read` (0x08000db8) checks only the return of two `rip2_get_data_ex` calls. It has no attribute or ACL check visible in this function.
- **The fallback table is byte-identical to `tools/hack-technicolor/osik/Technicolor.osik`** (256 bytes, sha256 prefix `1a8b5f07`, from the public `hack-technicolor/hack-technicolor` repo). It is not identical to the `Telia.osik` in the same folder (sha256 prefix `e55f0d9f`).
- **Consequence (DERIVED):** on this build, if item `0x120` is unreadable, `/proc/efu/info` prints the first word of a public Technicolor constant, not a device-unique value. The printed word on that path is `D9A2AECB`. No new key material is disclosed on that path.
- **Open:** whether item `0x120` is readable on the live device. If it is, the printed word is the device's own OSIK prefix. Nothing offline shows that. Reading `/proc/efu/info` on the device needs a shell, which is not available.

Key bytes are deliberately not reproduced in this file. Hashes and offsets are enough to reproduce the comparison.

## Second consumer of `EFU_getOSIK`: RSA-PSS verify block (partly resolved)

- **VERIFIED (disassembly):** the block at 0x08002270 (rizin label `fcn.08002270`, 384 bytes) starts with `cmp r4, 0x100`, so it runs only for a 256-byte input. It calls `EFU_getOSIK` into a stack buffer (`var_120h`, length 256), allocates a 208-byte object, calls `rsa_create_crypto`, builds a message from a caller string, a 4-byte stack word and a caller payload, calls `rsa_verifysig_pss_sha256`, and prints `== SIG VALID ==` or `== ! SIG INV ! ==` (strings at 0x08003e60, 0x08003e74).
- **CORRECTION (VERIFIED by reloc table):** I earlier said `EFU_isEngineeringFeatureUnlocked` (0x080026a4) calls this block. The call at 0x080026c0 has relocation `EFU_getBitmask` (0x0800249c), not `fcn.08002270`. That caller link is withdrawn. The true caller of the verify block is **not yet known**.
- **Derived (not established):** 256 bytes matches an RSA-2048 modulus or signature. Whether `var_120h` is the key, the signature or the message is **UNKNOWN** until the caller passes its arguments.
- **Not shown:** the key used by `rsa_create_crypto`; which caller reaches the block; whether `/proc/efu/temporal_tag` (`rip_efu_temporal_tag_proc_write`, 0x080026ec) is the path. Repo notes ([tried.md](tried.md)) say temporal tags are checked with RSA-PSS SHA-256, but that is a note, not a verified path here.

**Consequence:** the public fallback table is not yet shown to be a verification key. The claim "tag verification uses a public constant" is a **hypothesis**, not a finding.

## Caller map of the verify path (VERIFIED by BL scan, relocation table and mode bits)

Method: ARM `BL` immediates scanned over the whole `.ko` (any condition), plus `R_ARM_CALL` relocations. rizin's `fcn.*` / "CALL XREF" labels were not used, because they proved wrong twice.

| Function (entry) | Role | Call evidence |
| --- | --- | --- |
| `rip_efu_temporal_tag_proc_write` (≈0x080026ec) | `/proc/efu/temporal_tag` write handler | Its region reaches `__copy_from_user` (reloc 0x08002764) and `EFU_storeTemporalTag` (reloc 0x08002740) |
| `EFU_storeTemporalTag` (0x08002620) | stores a tag after checking it | Calls `verifyTag` at 0x0800262C |
| `EFU_verifyStoredTag` (0x080025d0) | checks a stored tag | Calls `verifyTag` at 0x08002600 |
| `EFU_getBitmask` (0x0800249C) | returns the bitmask after a check | Calls `verifyTag` at 0x0800253C |
| `verifyTag` (0x080023C4) | tag verification | Calls `isSignatureValid` at 0x08002488 |
| `isSignatureValid` (0x080021DC) | signature check | Its body contains the RSA-PSS verify block (0x08002270) with `SIG VALID` / `SIG INV` output |

- **VERIFIED:** `isSignatureValid` has exactly one BL caller (`verifyTag`). Nothing points to its entry through a pointer table.
- **VERIFIED:** `/proc/efu/temporal_tag` is registered with mode `0x1a4` (octal `0644`). Only the owner (root) can write it through normal permissions. An unprivileged user can read it but not write it.
- **Corrected:** the entry I called `fcn.08002270` is in the middle of `isSignatureValid`, not a separate function. The earlier "called from `EFU_isEngineeringFeatureUnlocked`" link was wrong.
- **Still unknown:** the RSA key used by `rsa_create_crypto`, and where the 256-byte OSIK value goes. The verify block reads OSIK into a 256-byte buffer before the check. Whether that buffer is the key, the signature or the message is not resolved.
- **Hypothesis unchanged:** "tags verify against the public Technicolor OSIK" is not shown. It would need the key path resolved first.

## Key search in `isSignatureValid` (partly resolved, not solved)

- **VERIFIED (raw bytes):** the relocated calls in this module are `BL` placeholders with immediate `0xFFFFFE` (`ebfffffe`), which branch to themselves. The real target is the relocation symbol. The `stmda` labels rizin printed for some call sites are mis-decodes. Scans for direct `BL` targets remain valid for non-relocated calls (e.g., `verifyTag` → `isSignatureValid` at 0x08002488, raw `ebffff53`).
- **VERIFIED (disassembly):** `isSignatureValid` runs a loop from 1 to 256 that prints its argument buffer byte by byte, then enters the RSA block. So the 256-byte argument is the signature, and the message is the caller string, a 4-byte word and the caller payload.
- **VERIFIED (relocations):** `rsa_create_crypto` (0x08002C24) is a LibTomCrypt RSA setup. It refers to `ltm_desc`, `ltc_mp`, and calls `mp_read_unsigned_bin`. So the key bytes come from a buffer passed into `rsa_create_crypto`.
- **Ruled out as a direct argument:** the 256-byte `EFU_getOSIK` buffer (`var_120h`) is not passed to `rsa_create_crypto` or `rsa_verifysig_pss_sha256` in the block I read. It is filled and not used there.
- **Open:** the key buffer that `rsa_create_crypto` reads from. In the block, its argument register is set from a kmem-cache object (`r6`, from `kmem_cache_alloc(malloc_sizes+0x64, 0xd0)`). I did not confirm that object is filled before the call. Whether it's a built-in key, or whether the key comes from a value outside this function, is **UNKNOWN**.
- **Consequence:** the public-OSIK-as-verification-key hypothesis is weaker, because the OSIK buffer is not an argument to the RSA calls. It is not disproven, but the direct link is not shown.

## Key buffer trace (not resolved)

- **VERIFIED (call-site setup):** in `isSignatureValid`, `rsa_create_crypto` is called with `r0 = &var_10h`, `r1 = 2`, `r2 = r6`, `r3 = 0x588`. `r6` is the result of `kmem_cache_alloc(malloc_sizes+0x64, 0xd0)`.
- **VERIFIED (inside `isSignatureValid`):** nothing writes to the memory `r6` points to. `r6` is used only as an argument (`rsa_create_crypto`, then `rsa_verifysig_pss_sha256` and `rsa_delete_crypto` as `r0`).
- **VERIFIED (inside `rsa_create_crypto`, 0x08002C24):** its second pointer argument (`r4 = r2`) is treated as the RSA context. It stores its own fields there (`[r4]`, `[r4+0x28]`, `[r4+0x30]`, `[r4+0x48]`) and calls `mp_init` on `r4+4` and `r4+0x14`. So `r6` is an RSA context allocated but not filled by this block, not a key blob.
- **Not established:** where the RSA key integers come from. The `mp_read_unsigned_bin` call inside `rsa_create_crypto` reads from a buffer whose origin I did not resolve. The public Technicolor OSIK is not passed to any of these calls.
- **Caution:** this is static reading of an uninitialised-looking context. It could be an incorrect argument mapping on my part. Confirming it needs the wrapper source or runtime evidence.

**Status:** the key is not found. No claim about verification with a public or constant key is supported by this trace.

## Next offline steps

1. Decode `EFU_getOSIK` (0x08002198) to see which bytes it returns and whether the printed word is a fixed prefix.
2. Trace the `rip_proc_new` pointer table at 0x08004210 to find its owning file and write path.
3. Confirm the target kernel for the live device before carrying any of this over.
