#!/usr/bin/env python3
"""Scan an image for a squashfs written as AES-XTS-plain64 (dm-crypt style).

For every 512-byte-aligned offset P, decrypt the 512 bytes at P as sector 0
(tweak 0) of a dm-crypt device starting at P, and report offsets where the
result begins with the squashfs magic b"hsqs".

The key is read from a log line, so it never appears on the command line or
in the output. A 32-byte key is AES-128-XTS, the same as a dm-crypt table key
of 64 hex characters.
"""

import argparse
import re
import sys

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SECTOR = 512
SQUASHFS_MAGIC = b"hsqs"
KEY_LINE = re.compile(rb"^([0-9a-f]{64})")


def read_key_from_log(path, line_no):
    """Return the 32-byte key from a 64-hex-character log line (1-based)."""
    with open(path, "rb") as handle:
        for index, line in enumerate(handle, start=1):
            if index == line_no:
                match = KEY_LINE.match(line)
                if not match:
                    raise ValueError(f"line {line_no} does not start with 64 hex characters")
                return bytes.fromhex(match.group(1).decode("ascii"))
    raise ValueError(f"line {line_no} not found in {path}")


def decrypt_sector0(key, sector):
    """Decrypt one 512-byte data unit with plain64 tweak 0."""
    cipher = Cipher(algorithms.AES(key), modes.XTS(bytes(16)))
    decryptor = cipher.decryptor()
    return decryptor.update(sector) + decryptor.finalize()


def scan(image, key):
    """Return file offsets whose XTS sector-0 decryption is a squashfs superblock."""
    hits = []
    for offset in range(0, len(image) - SECTOR + 1, SECTOR):
        plain = decrypt_sector0(key, image[offset:offset + SECTOR])
        if plain[:4] == SQUASHFS_MAGIC:
            hits.append(offset)
    return hits


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", help="file to scan")
    parser.add_argument("--key-log", required=True, help="log file that holds the key")
    parser.add_argument("--key-line", type=int, required=True, help="1-based line that starts with the key")
    args = parser.parse_args(argv)

    key = read_key_from_log(args.key_log, args.key_line)
    with open(args.image, "rb") as handle:
        image = handle.read()

    hits = scan(image, key)
    windows = len(image) // SECTOR
    print(f"scanned {windows} aligned windows in {args.image}")
    print(f"squashfs-magic hits: {len(hits)}")
    for offset in hits[:20]:
        print(f"  offset {offset} (0x{offset:x})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
