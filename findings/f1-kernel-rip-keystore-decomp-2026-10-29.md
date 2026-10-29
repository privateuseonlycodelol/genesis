# Technicolor eRIPv2 & Keystore Kernel Driver Decompilation (2026-10-29)

## Purpose

Perform deep binary decompilation and structural reverse engineering of Technicolor’s proprietary eRIPv2 driver (`ripdrv.arm.3.4.11-rt19.ko`) and memory secret reader (`r2secr.arm64.4.1.52.ko`) using the **REA (Reverse Engineer Anything)** toolchain and **Hopper Disassembler** to establish ground truth on key storage, hardware keystore integration, and `/proc/rip` visibility.

---

## 1. Executive Findings

1. **`OSCK` (Item `0x0121`) is Hardcoded Hidden from `/proc/rip`:**
   - In `rip_proc_init` (decompiled at address `0x1dfc`), the directory enumeration loop contains an explicit check:
     ```c
     r5 = 0x121;
     r2 = var_2A; // current item ID
     if (zero_extend_32(r2) == r5) continue;
     ```
   - **VERIFIED:** Even with a local root shell and full read access to `/proc/rip/`, Item `0x0121` (`RIP_ID_OSCK`) will **never** be exposed as a virtual filesystem entry. The driver deliberately suppresses it to protect firmware decryption keys from being read by user-space diagnostics.

2. **Unified PEM Structure in Item `0x011A` (`CLIENT_CERTIFICATE`):**
   - In `rip2_get_cert_privkey_position` (`0x102c`), the driver scans for eight distinct PEM markers:
     - `-----BEGIN CERTIFICATE-----` / `-----END CERTIFICATE-----`
     - `-----BEGIN PRIVATE KEY-----` / `-----END PRIVATE KEY-----`
     - `-----BEGIN RSA PRIVATE KEY-----` / `-----END RSA PRIVATE KEY-----`
     - `-----BEGIN ENCRYPTED PRIVATE KEY-----` / `-----END ENCRYPTED PRIVATE KEY-----`
   - **VERIFIED:** Item `0x011A` contains **both** the X.509 client certificate and the corresponding RSA/ECC private key inside a single contiguous buffer.

3. **eRIPv2 Item Cryptographic Signature & Padding Scheme:**
   - In `rip2_crypto_process` (`0x3320`), items flagged with attribute `0x10000000` (`ATTR_EIK_SIGN`) and `0x08000000` (`ATTR_ECK_ENCR`) are decrypted using **AES-128-CBC** (`eck`).
   - The decrypted payload contains the data plus a 256-byte signature.
   - The signature verification prepends the 16-bit Item ID to the data:
     `payload = (uint16_t)item_id || data`
   - It verifies this payload using **RSA-PSS with SHA-256** against `eik` (`RIP_ID_EIK`, Item `0x011E`, 2048-bit RSA public key).

4. **`r2secr` In-Memory Data Structure (`r2secr.arm64.4.1.52.ko`):**
   - Decompilation of `init_module` (`0x140`) shows the in-memory eRIP table passed by bootloaders:
     ```c
     printk("r2secr : %lx \n", *r2secr);
     r19 = (*r2secr - *memstart_addr) + 0xffffffc000000008;
     while (*(int16_t *)r19 != 0x0) {
         id = *(int16_t *)r19;
         length = r19[1];
         data_ptr = r19[2];
         DumpHex(data_ptr - *memstart_addr + PAGE_OFFSET);
         r19 += 0x10; // 16-byte descriptor
     }
     ```
   - Each item in memory is described by a 16-byte record: `[ID: uint16, flags: uint16, length: uint32, data_phys_addr: uint64]`.

---

## 2. Procedure Decompilation Records

### A. Dynamic Control Nodes in `rip_proc_init` (`0x1dfc`)
```c
// Decompiled via REA / Hopper
r0 = proc_mkdir("rip", NULL);
*proc_rip_dir = r0;
if (r0 != NULL) {
    while (rip2_get_next(&item_iter, 0xffffffff, &item_id) == 1) {
        // Suppress item 0x121 (OSCK) from ever appearing in /proc/rip/
        if (zero_extend_32(item_id) == 0x121) {
            continue;
        }
        // Suppress if hidden attribute flags are active
        if ((item_flags & 0x6000000) != 0) {
            continue;
        }
        sprintf(entry_name, "%04x", item_id);
        rip_proc_add_entry(entry_name, mode, fops, 1);
    }
    // Register special control nodes
    rip_proc_add_entry("new", 0x1a4, &rip_proc_new_fops, 0);
    rip_proc_add_entry("lock", 0x1a4, &rip_proc_lock_fops, 0);
    rip_proc_add_entry("signed", 0x1a4, &rip_proc_signed_fops, 0);
    rip_proc_add_entry("encrypt", 0x1a4, &rip_proc_encrypt_fops, 0);
}
```

### B. Item Registration Blacklist in `rip_proc_new` (`0x1584`)
When user-space writes an item ID to `/proc/rip/new` to create a virtual entry:
```c
// Decompiled via REA / Hopper
sscanf(buf, "%x", &item_id);
switch (item_id) {
    case 282: // 0x011A = RIP_ID_CLIENT_CERTIFICATE
        return -EEXIST;
    case 289: // 0x0121 = RIP_ID_OSCK
        return -EEXIST;
    default:
        // Allows creating virtual entries for any unblacklisted ID
        rip_proc_add_entry(item_name, 0x1a4, fops, 1);
        break;
}
```

### C. Live Flash Mutation in `rip_proc_write` (`0x12c4`) and `rip2_drv_write` (`0x944`)
- Writing to `/proc/rip/<item_id>` copies data from user space and invokes `rip2_drv_write`:
  - If the item does not exist: calls `rip2_add_item` and writes directly to flash media.
  - If the item exists and lock bit `0x40000000` is clear: updates the item, invalidates the old entry, and calls `rip2_flash_write` to commit the modified bytes directly into flash memory!
  - If lock bit `0x40000000` is set: returns `-EBUSY` / `-EPERM`.

### D. In-Kernel Encryption via `/proc/rip/encrypt` (`0x18e0` / `0xc38`)
- Writing an item ID to `/proc/rip/encrypt` triggers `rip2_encrypt`:
  - Reads plaintext item data via `rip2_get_data_ex`.
  - Invokes `rip2_crypto_encrypt_with_ECK` using the in-kernel **`ECK` key** (Hardware Keystore Slot `0x114`).
  - Writes the re-encrypted ciphertext back to flash with attribute `ATTR_ECK_ENCR` (`0x08000000`) set.

### B. Key Import Constraints (`rip2_crypto_import_eck` & `import_eik`)
* **`rip2_crypto_import_eck` (`0x32c0`):**
  - Enforces `arg1 == 0x10` (strictly 16 bytes / 128-bit AES key).
  - Associates key with hardware slot `0x114`.
* **`rip2_crypto_import_eik` (`0x3270`):**
  - Enforces `arg1 == 0x100` (strictly 256 bytes / 2048-bit RSA public key modulus).

---

## 3. The Complete Cryptographic Relationship Map

```mermaid
flowchart TD
    A["NAND Flash: eripv2_bak1 / eripv2_bak2\n(Offset 0x00800000 / 0x00900000)"] --> B["eRIPv2 Binary Partition"]
    B -->|Decrypt with ECK / Slot 0x114| C["Decrypted In-Memory eRIP Items"]
    C --> D["Item 0x0108: RANDOM_KEY_B (64B)\n[0:32] AES-256 for export_config\n[0:64] HMAC-SHA1 signature key"]
    C --> E["Item 0x011A: CLIENT_CERTIFICATE\n(Unified PEM: Cert + Private Key for mTLS)"]
    C --> F["Item 0x011E: EIK\n(2048-bit RSA Public Key for item PSS verification)"]
    C --> G["Item 0x0120: OSIK\n(2048-bit RSA Public Key for /proc/efu signatures)"]
    C --> H["Item 0x0121: OSCK (AES Key)\n[Suppressed from /proc/rip/]\nUsed by blidec to decrypt RBI payload"]
```

---

## 4. Impact on Current Research

1. **Why `cat /proc/rip/0121` is impossible:**
   - Previous hypotheses proposed reading `/proc/rip/0121` once root was achieved to get the OSCK. This decompilation **proves that `/proc/rip/0121` does not exist in the virtual filesystem by design**.
   - To obtain `OSCK`, an attacker must either:
     a) Dump raw physical memory where U-Boot / kernel unpacked `r2secr`.
     b) Dump the raw `eripv2` partition from NAND and decrypt it with `ECK` using `scripts/eripv2.py`.
2. **Why `RIP_ID_RANDOM_KEY_B` (Item `0x0108`) IS readable:**
   - Item `0x0108` has no suppression filter and is exposed under `/proc/rip/0108` on systems where the driver is active, directly unlocking `scripts/decrypt_f1_config_export.py`.
3. **Firmware Decryption Independence:**
   - Because our target build `23.1.b` uses **dm-crypt `aes-xts-plain64`** with the **L598 key** (already captured on UART boot), **we do not need `OSCK` to decrypt the live router's root filesystem**. `OSCK` is only needed for sealed offline `.rbi` files.
