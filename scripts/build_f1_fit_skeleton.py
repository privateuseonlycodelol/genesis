#!/usr/bin/env python3
"""Build and inspect minimal Flattened Image Tree (FIT / ITB) images for Telia F1 / GCNT-X.

Generates valid Flattened Device Tree binary blobs (magic 0xd00dfeed) structured according
to the U-Boot FIT image specification. Resolves the FDT_ERR_BADMAGIC failure observed
in live BOOTP/TFTP recovery ('action 3Can't find images parent node /images').

No external dependencies (no dtc or mkimage required). Pure Python implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path


class FdtWriter:
    """Encodes a Devicetree / FIT image into valid FDT binary format (Devicetree Spec v0.4)."""

    FDT_MAGIC = 0xD00DFEED
    FDT_BEGIN_NODE = 1
    FDT_END_NODE = 2
    FDT_PROP = 3
    FDT_NOP = 4
    FDT_END = 9

    def __init__(self) -> None:
        self.struct_data = bytearray()
        self.strings_data = bytearray()
        self.strings_offsets: dict[str, int] = {}

    def _add_string(self, s: str) -> int:
        if s in self.strings_offsets:
            return self.strings_offsets[s]
        offset = len(self.strings_data)
        self.strings_data.extend(s.encode("ascii") + b"\x00")
        self.strings_offsets[s] = offset
        return offset

    def begin_node(self, name: str) -> None:
        self.struct_data.extend(struct.pack("!I", self.FDT_BEGIN_NODE))
        name_bytes = name.encode("ascii") + b"\x00"
        pad = (4 - (len(name_bytes) % 4)) % 4
        self.struct_data.extend(name_bytes + b"\x00" * pad)

    def end_node(self) -> None:
        self.struct_data.extend(struct.pack("!I", self.FDT_END_NODE))

    def property(self, name: str, value: bytes) -> None:
        nameoff = self._add_string(name)
        val_len = len(value)
        self.struct_data.extend(struct.pack("!III", self.FDT_PROP, val_len, nameoff))
        pad = (4 - (val_len % 4)) % 4
        self.struct_data.extend(value + b"\x00" * pad)

    def property_string(self, name: str, value: str) -> None:
        self.property(name, value.encode("ascii") + b"\x00")

    def property_u32(self, name: str, value: int) -> None:
        self.property(name, struct.pack("!I", value))

    def property_u64(self, name: str, value: int) -> None:
        self.property(name, struct.pack("!Q", value))

    def build(self) -> bytes:
        struct_bytes = self.struct_data + struct.pack("!I", self.FDT_END)
        pad_struct = (4 - (len(struct_bytes) % 4)) % 4
        struct_bytes += b"\x00" * pad_struct

        header_len = 40
        rsvmap_len = 16  # Empty reservation map (two 64-bit zero entries)
        rsvmap = b"\x00" * 16

        off_mem_rsvmap = header_len
        off_dt_struct = off_mem_rsvmap + rsvmap_len
        off_dt_strings = off_dt_struct + len(struct_bytes)
        totalsize = off_dt_strings + len(self.strings_data)

        header = struct.pack(
            "!IIIIIIIIII",
            self.FDT_MAGIC,
            totalsize,
            off_dt_struct,
            off_dt_strings,
            off_mem_rsvmap,
            17,  # version
            16,  # last_comp_version
            0,   # boot_cpuid_phys
            len(self.strings_data),
            len(struct_bytes),
        )
        return header + rsvmap + struct_bytes + bytes(self.strings_data)


class FdtReader:
    """Parses and inspects an FDT / FIT binary blob."""

    FDT_MAGIC = 0xD00DFEED
    FDT_BEGIN_NODE = 1
    FDT_END_NODE = 2
    FDT_PROP = 3
    FDT_NOP = 4
    FDT_END = 9

    def __init__(self, data: bytes) -> None:
        if len(data) < 40:
            raise ValueError(f"Data too short for FDT header: {len(data)} bytes")
        fields = struct.unpack("!IIIIIIIIII", data[:40])
        self.magic = fields[0]
        if self.magic != self.FDT_MAGIC:
            raise ValueError(f"Invalid FDT magic: {hex(self.magic)} (expected 0xd00dfeed)")
        self.totalsize = fields[1]
        self.off_dt_struct = fields[2]
        self.off_dt_strings = fields[3]
        self.off_mem_rsvmap = fields[4]
        self.version = fields[5]
        self.last_comp_version = fields[6]
        self.boot_cpuid_phys = fields[7]
        self.size_dt_strings = fields[8]
        self.size_dt_struct = fields[9]

        self.data = data
        self.strings = data[self.off_dt_strings : self.off_dt_strings + self.size_dt_strings]

    def _get_string(self, offset: int) -> str:
        nul = self.strings.find(b"\x00", offset)
        if nul == -1:
            return self.strings[offset:].decode("ascii", "replace")
        return self.strings[offset:nul].decode("ascii", "replace")

    def walk(self) -> tuple[list[str], dict[str, bytes]]:
        """Traverse the structure tree. Return (node_paths, properties_dict)."""
        offset = self.off_dt_struct
        stack: list[str] = []
        nodes: list[str] = []
        props: dict[str, bytes] = {}

        end_offset = self.off_dt_struct + self.size_dt_struct
        while offset < end_offset:
            tag = struct.unpack("!I", self.data[offset : offset + 4])[0]
            offset += 4

            if tag == self.FDT_BEGIN_NODE:
                nul = self.data.find(b"\x00", offset)
                name = self.data[offset:nul].decode("ascii", "replace")
                name_len = (nul - offset) + 1
                offset += name_len + ((4 - (name_len % 4)) % 4)
                stack.append(name)
                path = "/" + "/".join(s for s in stack if s)
                nodes.append(path)

            elif tag == self.FDT_END_NODE:
                if stack:
                    stack.pop()

            elif tag == self.FDT_PROP:
                val_len, nameoff = struct.unpack("!II", self.data[offset : offset + 8])
                offset += 8
                val = self.data[offset : offset + val_len]
                pad = (4 - (val_len % 4)) % 4
                offset += val_len + pad
                prop_name = self._get_string(nameoff)
                curr_path = "/" + "/".join(s for s in stack if s)
                props[f"{curr_path}:{prop_name}"] = val

            elif tag == self.FDT_NOP:
                continue

            elif tag == self.FDT_END:
                break
            else:
                raise ValueError(f"Unknown FDT tag {tag} at offset {offset - 4}")

        return nodes, props


def build_minimal_fit_skeleton(
    description: str = "Telia F1 GCNT-X recovery skeleton",
) -> bytes:
    """Build the smallest valid FIT image with root properties and an empty /images node."""
    w = FdtWriter()
    w.begin_node("")  # Root
    w.property_string("description", description)
    w.property_u32("#address-cells", 1)

    # Required parent node that U-Boot's fit_image_get_node() checks
    w.begin_node("images")
    w.end_node()  # images

    w.end_node()  # Root
    return w.build()


def build_standard_fit_skeleton(
    description: str = "Telia F1 GCNT-X recovery test image",
    payload_data: bytes = b"INERT-TEST-PAYLOAD\n",
    compact: bool = False,
    board: str = "GCNT-X",
    rootfs_data: bytes | None = None,
    bootfs_data: bytes | None = None,
) -> bytes:
    """Build a complete FIT image with /images/kernel-1 and /configurations/config-1.

    When bootfs_data or rootfs_data is given, add /images/bootfs and/or /images/rootfs
    and point config-1 at them with bootfs = "bootfs" and/or rootfs = "rootfs".
    The BOOTP recovery bundle handler (U-Boot sdk_test_commands.c flash_upgrade_img_bundle)
    looks up configuration property names: bootfs, rootfs, loader, rootfs_data, ramfs_rd
    (UART evidence in findings/f1-bootp-lan-2026-10-13.md, Addendum 8).
    """
    w = FdtWriter()
    w.begin_node("")  # Root
    w.property_string("description", "F1" if compact else description)
    w.property_u32("#address-cells", 1)
    w.property_string("compatible", board)

    # /compatible subnode in bundle
    w.begin_node("compatible")
    w.property_string("board", board)
    w.property_string("model", board)
    w.property_string("compatible", board)
    w.end_node()  # compatible

    # /images node
    w.begin_node("images")

    # /images/kernel-1
    w.begin_node("kernel-1")
    if not compact:
        w.property_string("description", "AArch64 test recovery kernel component")
    w.property("data", payload_data)
    w.property_string("type", "kernel")
    w.property_string("arch", "arm64")
    w.property_string("os", "linux")
    w.property_string("compression", "none")
    if not compact:
        w.property_u32("load", 0x00100000)
        w.property_u32("entry", 0x00100000)

    # /images/kernel-1/hash-1
    w.begin_node("hash-1")
    w.property_string("algo", "sha256")
    w.property("value", hashlib.sha256(payload_data).digest())
    w.end_node()  # hash-1

    w.end_node()  # kernel-1

    # /images/bootfs (only when a boot filesystem / kernel FIT is packaged)
    if bootfs_data is not None:
        w.begin_node("bootfs")
        if not compact:
            w.property_string("description", "Boot filesystem / kernel FIT component")
        w.property("data", bootfs_data)
        w.property_string("type", "firmware")
        w.property_string("arch", "arm64")
        w.property_string("os", "linux")
        w.property_string("compression", "none")

        w.begin_node("hash-1")
        w.property_string("algo", "sha256")
        w.property("value", hashlib.sha256(bootfs_data).digest())
        w.end_node()  # hash-1

        w.end_node()  # bootfs

    # /images/rootfs (only when a root filesystem is packaged)
    if rootfs_data is not None:
        w.begin_node("rootfs")
        if not compact:
            w.property_string("description", "SquashFS root filesystem component")
        w.property("data", rootfs_data)
        w.property_string("type", "filesystem")
        w.property_string("arch", "arm64")
        w.property_string("os", "linux")
        w.property_string("compression", "none")

        w.begin_node("hash-1")
        w.property_string("algo", "sha256")
        w.property("value", hashlib.sha256(rootfs_data).digest())
        w.end_node()  # hash-1

        w.end_node()  # rootfs

    w.end_node()  # images

    # /configurations node
    w.begin_node("configurations")
    w.property_string("default", "config-1")

    # /configurations/config-1
    w.begin_node("config-1")
    if not compact:
        w.property_string("description", "Default recovery boot configuration")
    w.property_string("kernel", "kernel-1")
    if bootfs_data is not None:
        w.property_string("bootfs", "bootfs")
    if rootfs_data is not None:
        w.property_string("rootfs", "rootfs")
    w.property_string("compatible", board)

    # /configurations/config-1/compatible subnode
    w.begin_node("compatible")
    w.property_string("board", board)
    w.property_string("compatible", board)
    w.end_node()  # compatible

    w.end_node()  # config-1
    w.end_node()  # configurations

    w.end_node()  # Root
    return w.build()


def build_inner_bootfs_fit(
    kernel_data: bytes,
    dtb_data: bytes | None = None,
    board: str = "GCNT-X",
    description: str = "Telia F1 GCNT-X inner bootfs FIT",
    load_addr: int = 0x01000000,
    entry_addr: int = 0x01000000,
) -> bytes:
    """Build an inner bootfs FIT image containing kernel and conf_linux/conf_lx_<board>.

    Omits /brcm_rootfs_encrypt so Broadcom U-Boot's bcm_handle_mapper() falls back to
    unencrypted, non-dm-verity SquashFS mounting (root=/dev/ubiblock0_<volid>).
    """
    w = FdtWriter()
    w.begin_node("")  # Root
    w.property_string("description", description)
    w.property_u32("#address-cells", 1)

    # /images node
    w.begin_node("images")

    # /images/kernel-1
    w.begin_node("kernel-1")
    w.property_string("description", "Linux kernel")
    w.property("data", kernel_data)
    w.property_string("type", "kernel")
    w.property_string("arch", "arm64")
    w.property_string("os", "linux")
    w.property_string("compression", "none")
    w.property_u32("load", load_addr)
    w.property_u32("entry", entry_addr)

    w.begin_node("hash-1")
    w.property_string("algo", "sha256")
    w.property("value", hashlib.sha256(kernel_data).digest())
    w.end_node()  # hash-1

    w.end_node()  # kernel-1

    if dtb_data is not None:
        w.begin_node("fdt-1")
        w.property_string("description", f"Flattened Device Tree for {board}")
        w.property("data", dtb_data)
        w.property_string("type", "flat_dt")
        w.property_string("arch", "arm64")
        w.property_string("compression", "none")

        w.begin_node("hash-1")
        w.property_string("algo", "sha256")
        w.property("value", hashlib.sha256(dtb_data).digest())
        w.end_node()  # hash-1

        w.end_node()  # fdt-1

    w.end_node()  # images

    # /configurations node
    w.begin_node("configurations")
    w.property_string("default", "conf_linux")

    # conf_linux
    w.begin_node("conf_linux")
    w.property_string("description", "Standard Linux boot configuration")
    w.property_string("kernel", "kernel-1")
    if dtb_data is not None:
        w.property_string("fdt", "fdt-1")
    w.property_string("compatible", board)
    w.end_node()

    # conf_lx_<board>
    board_conf_name = f"conf_lx_{board}"
    w.begin_node(board_conf_name)
    w.property_string("description", f"Board-specific Linux boot configuration for {board}")
    w.property_string("kernel", "kernel-1")
    if dtb_data is not None:
        w.property_string("fdt", "fdt-1")
    w.property_string("compatible", board)
    w.end_node()

    w.end_node()  # configurations
    w.end_node()  # Root
    return w.build()


def inspect_fit_file(path: Path) -> None:
    """Parse and print FDT details from a file."""
    data = path.read_bytes()
    reader = FdtReader(data)
    nodes, props = reader.walk()

    print(f"=== FDT Header: {path} ===")
    print(f"Magic:              {hex(reader.magic)} (valid)")
    print(f"Total size:         {reader.totalsize} bytes (file length: {len(data)})")
    print(f"Version:            {reader.version} (last compatible: {reader.last_comp_version})")
    print(f"Struct offset:      {reader.off_dt_struct} (size: {reader.size_dt_struct})")
    print(f"Strings offset:     {reader.off_dt_strings} (size: {reader.size_dt_strings})")
    print(f"\n=== Nodes ({len(nodes)}) ===")
    for n in nodes:
        print(f"  {n}")

    print(f"\n=== Properties ({len(props)}) ===")
    for key, val in props.items():
        # Try decoding as null-terminated ASCII string
        if val.endswith(b"\x00") and all(32 <= b < 127 for b in val[:-1]):
            val_str = repr(val[:-1].decode("ascii"))
        elif len(val) == 4:
            val_u32 = struct.unpack("!I", val)[0]
            val_str = f"{val_u32} ({hex(val_u32)})"
        elif len(val) == 32:
            val_str = f"hex({val.hex()})"
        else:
            val_str = f"bytes[{len(val)}] {val[:16].hex()}..."
        print(f"  {key} = {val_str}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", "-o", help="Output path for generated FIT image")
    parser.add_argument(
        "--mode",
        choices=["minimal", "standard"],
        default="standard",
        help="minimal (only /images) or standard (with kernel-1 and config-1)",
    )
    parser.add_argument("--compact", action="store_true", help="Generate compact standard FIT image (<512B)")
    parser.add_argument("--description", default="Telia F1 GCNT-X recovery test image")
    parser.add_argument("--payload-text", default="INERT-TEST-PAYLOAD\n", help="Dummy payload text")
    parser.add_argument(
        "--bootfs",
        help="Boot filesystem / kernel FIT image to package as /images/bootfs (standard mode only)",
    )
    parser.add_argument(
        "--rootfs",
        help="SquashFS image to package as /images/rootfs (standard mode only)",
    )
    parser.add_argument("--inspect", help="Inspect and dump an existing FIT / DTB file")
    args = parser.parse_args()

    if args.inspect:
        inspect_fit_file(Path(args.inspect))
        return 0

    if not args.out:
        print("ERROR: Specify --out <path> or --inspect <path>", file=sys.stderr)
        return 1

    bootfs_data = None
    if args.bootfs:
        if args.mode != "standard":
            print("ERROR: --bootfs requires --mode standard", file=sys.stderr)
            return 1
        bootfs_data = Path(args.bootfs).read_bytes()

    rootfs_data = None
    if args.rootfs:
        if args.mode != "standard":
            print("ERROR: --rootfs requires --mode standard", file=sys.stderr)
            return 1
        rootfs_data = Path(args.rootfs).read_bytes()
        # SquashFS superblock magic is little-endian 'hsqs' at offset 0
        if rootfs_data[:4] != b"hsqs":
            print(f"ERROR: {args.rootfs} does not start with SquashFS magic 'hsqs'", file=sys.stderr)
            return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.mode == "minimal":
        blob = build_minimal_fit_skeleton(description=args.description)
    else:
        blob = build_standard_fit_skeleton(
            description=args.description,
            payload_data=args.payload_text.encode("utf-8"),
            compact=args.compact,
            rootfs_data=rootfs_data,
            bootfs_data=bootfs_data,
        )

    out_path.write_bytes(blob)
    print(f"[+] Wrote {len(blob)} bytes of valid FIT image ({args.mode} mode) to {out_path}")
    inspect_fit_file(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
