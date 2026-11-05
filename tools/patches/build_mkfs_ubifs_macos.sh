#!/usr/bin/env bash
# Build native mkfs.ubifs for macOS (Darwin arm64/x86_64) using mtd-utils + Darwin compat patch
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${BUILD_DIR:-/tmp/mtd-utils-build}"
PATCH_FILE="${SCRIPT_DIR}/mtd-utils-macos.patch"
OUT_BIN="${REPO_ROOT}/tools/bin/mkfs.ubifs"

echo "[*] Ensuring prerequisite build tools (autoconf, automake, libtool)..."
if ! command -v autoconf >/dev/null 2>&1 || ! command -v automake >/dev/null 2>&1; then
    if command -v brew >/dev/null 2>&1; then
        brew install autoconf automake libtool
    else
        echo "[-] Error: autoconf/automake not found. Install via Homebrew: brew install autoconf automake" >&2
        exit 1
    fi
fi

echo "[*] Cloning mtd-utils..."
rm -rf "${BUILD_DIR}"
git clone --depth 1 https://github.com/sigma-star/mtd-utils.git "${BUILD_DIR}"

echo "[*] Applying macOS compatibility patch..."
cd "${BUILD_DIR}"
git apply "${PATCH_FILE}"

echo "[*] Generating configure scripts..."
./autogen.sh

echo "[*] Configuring mtd-utils for host tools..."
./configure --without-xattr --without-zstd --without-crypto

echo "[*] Compiling mkfs.ubifs..."
make mkfs.ubifs

echo "[*] Installing mkfs.ubifs to ${OUT_BIN}..."
mkdir -p "${REPO_ROOT}/tools/bin"
cp mkfs.ubifs "${OUT_BIN}"
chmod +x "${OUT_BIN}"

echo "[+] Successfully built and installed: ${OUT_BIN}"
"${OUT_BIN}" -V || true
