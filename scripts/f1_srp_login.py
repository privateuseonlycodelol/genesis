#!/usr/bin/env python3
"""Technicolor Homeware SRP login (matches /js/srp-min.js).

Password for `proof`: prefer `--password-file`; `F1_PASSWORD` env is legacy.
"""
import hashlib
import json
import os
import re
import secrets
import sys
import urllib.parse
import urllib.request
from http.cookiejar import MozillaCookieJar
from pathlib import Path

from f1_secrets import read_password_file, validate_router_base

N = int(
    "ac6bdb41324a9a9bf166de5e1389582faf72b6651987ee07fc3192943db56050a37329cbb4"
    "a099ed8193e0757767a13dd52312ab4b03310dcd7f48a9da04fd50e8083969edb767b0cf6095179"
    "a163ab3661a05fbd5faaae82918a9962f0b93b855f97993ec975eeaa80d740adbf4ff747359d041d"
    "5c33ea71d281e446b14773bca97b43a23fb801676bd207a436c6481f1d2b9078717461a5b9d32e688"
    "f87748544523b524b0d57d5ea77a2775d2ecfa032cfbdbf52fb3786160279004e57ae6af874e7303"
    "ce53299ccc041c7bc308d82a5698f3a8d0c38271ae35f8e9dbfbb694b5c803d89f7ae435de236d525f"
    "54759b65e372fcd68ef20fa7111f9e4aff73",
    16,
)
G = 2
K_MULT = int("05b9e8ef059c6b32ea59fc1d322d37f04aa30bae5aa9003b8321e21ddb04e300", 16)
U_HASH = "4a76a9a2402bdd18123389b72ebbda50a30f65aedb90d7273130edea4b29cc4c"
Q = 256


def sha256_hex_text(s: str) -> str:
    return hashlib.sha256(s.encode("latin-1", errors="surrogatepass") if False else s.encode("utf-8")).hexdigest()


def sha256_hex_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def even_hex(h: str) -> str:
    h = h.strip()
    if len(h) % 2:
        h = "0" + h
    return h


def sha256_hex_of_hex(hexstr: str) -> str:
    """Match jsSHA(input, \"HEX\").getHash(\"SHA-256\", \"HEX\")."""
    return hashlib.sha256(bytes.fromhex(even_hex(hexstr))).hexdigest()


def utf8_encode_js(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        d = ord(s[i])
        e = ord(s[i + 1]) if i + 1 < len(s) else 0
        if 0xD800 <= d <= 0xDBFF and 0xDC00 <= e <= 0xDFFF:
            d = 0x10000 + ((d & 0x3FF) << 10) + (e & 0x3FF)
            i += 1
        if d <= 0x7F:
            out.append(chr(d))
        elif d <= 0x7FF:
            out.append(chr(0xC0 | (d >> 6)) + chr(0x80 | (d & 0x3F)))
        elif d <= 0xFFFF:
            out.append(
                chr(0xE0 | (d >> 12))
                + chr(0x80 | ((d >> 6) & 0x3F))
                + chr(0x80 | (d & 0x3F))
            )
        else:
            out.append(
                chr(0xF0 | (d >> 18))
                + chr(0x80 | ((d >> 12) & 0x3F))
                + chr(0x80 | ((d >> 6) & 0x3F))
                + chr(0x80 | (d & 0x3F))
            )
        i += 1
    return "".join(out)


def to_byte_array(n: int) -> bytearray:
    """Match JavaScript BigInteger.toByteArray() (signed-magnitude style)."""
    if n == 0:
        return bytearray([0])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    if b[0] & 0x80:
        b = b"\x00" + b
    return bytearray(b)


def pad256_bytes(b: bytearray) -> bytes:
    if len(b) > Q:
        b = b[1:]
    return bytes(Q - len(b)) + bytes(b)


def compute_u(A: int, B: int) -> int:
    a_bytes = pad256_bytes(to_byte_array(A))
    b_bytes = pad256_bytes(to_byte_array(B))
    return int(sha256_hex_bytes(a_bytes + b_bytes), 16)


class SRPClient:
    def __init__(self, jar_path: str, base: str):
        self.base = validate_router_base(base)
        self.jar = MozillaCookieJar(jar_path)
        if os.path.exists(jar_path):
            self.jar.load(ignore_discard=True, ignore_expires=True)
        self.csrf = ""
        self.F = 0
        self.A_int = 0
        self.A_hex = ""
        self.B_proof = ""
        self.y_hex = ""
        self.v_hex = ""

    def _open(self, url: str, data=None, method="GET", timeout=30):
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        with opener.open(req, timeout=timeout) as resp:
            return resp.getcode(), resp.read()

    def save_jar(self):
        self.jar.save(ignore_discard=True, ignore_expires=True)

    def load_csrf(self, html: str):
        m = re.search(r'CSRFtoken"\s+content\s*=\s*"([^"]+)"', html, re.I)
        if not m:
            raise RuntimeError("CSRF token not found")
        self.csrf = m.group(1)

    def gen_A(self):
        while True:
            self.F = secrets.randbits(256)
            self.A_int = pow(G, self.F, N)
            if self.A_int % N == 0:
                continue
            self.A_hex = format(self.A_int, "x")
            if len(self.A_hex) % 2:
                self.A_hex = "0" + self.A_hex
            return

    def login(self, username: str, password: str):
        self.gen_A()
        post1 = urllib.parse.urlencode(
            {"CSRFtoken": self.csrf, "I": username, "A": self.A_hex}
        ).encode()
        code1, body1 = self._open(f"{self.base}/authenticate", post1, "POST")
        self.save_jar()
        if code1 == 503:
            return 503, "503 on identify"
        try:
            r1 = json.loads(body1.decode())
        except json.JSONDecodeError:
            return code1, body1[:200]

        salt = r1.get("s")
        B_hex = r1.get("B")
        if not salt or not B_hex:
            return code1, r1

        B_int = int(B_hex, 16)
        u_scramble = compute_u(self.A_int, B_int)
        if B_int % N == 0 or u_scramble == 0:
            return 400, "bad B"

        user_pass = utf8_encode_js(f"{username}:{password}")
        x = int(sha256_hex_of_hex(even_hex(salt) + sha256_hex_text(user_pass)), 16)
        n = pow(G, x, N)
        u_part = (K_MULT * n) % N
        t = (B_int - u_part) % N
        exp = (self.F + u_scramble * x) % N
        client_key = pow(t, exp, N)
        s_hex = even_hex(format(client_key, "x"))
        s_hash = sha256_hex_of_hex(s_hex)
        self.B_proof = s_hash

        user_hash = sha256_hex_text(utf8_encode_js(username))
        self.y_hex = sha256_hex_of_hex(
            U_HASH + user_hash + even_hex(salt) + even_hex(self.A_hex) + even_hex(B_hex) + s_hash
        )
        self.v_hex = sha256_hex_of_hex(even_hex(self.A_hex) + self.y_hex + s_hash)

        post2 = urllib.parse.urlencode({"CSRFtoken": self.csrf, "M": self.y_hex}).encode()
        code2, body2 = self._open(f"{self.base}/authenticate", post2, "POST")
        self.save_jar()
        if code2 == 503:
            return 503, "503 on verify"
        try:
            r2 = json.loads(body2.decode())
        except json.JSONDecodeError:
            return code2, body2[:200]

        if r2.get("M", "").upper() == self.v_hex.upper():
            return 200, "ok"
        return 401, r2


def crypto_prepare() -> dict:
    F = secrets.randbits(256)
    while True:
        A_int = pow(G, F, N)
        if A_int % N == 0:
            F = secrets.randbits(256)
            continue
        A_hex = format(A_int, "x")
        if len(A_hex) % 2:
            A_hex = "0" + A_hex
        return {"F": F, "A_hex": A_hex, "A_int": A_int}


def crypto_proof(
    F: int, A_hex: str, A_int: int, username: str, password: str, salt: str, B_hex: str
) -> dict:
    B_int = int(B_hex, 16)
    u_scramble = compute_u(A_int, B_int)
    if B_int % N == 0 or u_scramble == 0:
        raise ValueError("bad B")
    user_pass = utf8_encode_js(f"{username}:{password}")
    x = int(sha256_hex_of_hex(even_hex(salt) + sha256_hex_text(user_pass)), 16)
    n = pow(G, x, N)
    u_part = (K_MULT * n) % N
    t = (B_int - u_part) % N
    exp = (F + u_scramble * x) % N
    client_key = pow(t, exp, N)
    s_hex = even_hex(format(client_key, "x"))
    s_hash = sha256_hex_of_hex(s_hex)
    user_hash = sha256_hex_text(utf8_encode_js(username))
    y_hex = sha256_hex_of_hex(
        U_HASH + user_hash + even_hex(salt) + even_hex(A_hex) + even_hex(B_hex) + s_hash
    )
    v_hex = sha256_hex_of_hex(even_hex(A_hex) + y_hex + s_hash)
    return {"M": y_hex, "v": v_hex, "B_proof": s_hash}


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "prepare":
        print(json.dumps(crypto_prepare()))
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "proof":
        state = json.load(sys.stdin)
        rest = sys.argv[2:]
        identify_path = None
        password_file = None
        idx = 0
        while idx < len(rest):
            if rest[idx] == "--password-file" and idx + 1 < len(rest):
                password_file = rest[idx + 1]
                idx += 2
                continue
            if identify_path is None:
                identify_path = rest[idx]
                idx += 1
                continue
            print("unexpected argument: " + rest[idx], file=sys.stderr)
            sys.exit(2)
        if not identify_path:
            print("usage: proof <auth-identify.json> [--password-file PATH]", file=sys.stderr)
            sys.exit(2)
        resp = json.load(open(identify_path, encoding="utf-8"))
        user = os.environ.get("F1_USER", "User")
        if password_file:
            password = read_password_file(Path(password_file))
        else:
            password = os.environ.get("F1_PASSWORD", "")
        if not password:
            sys.exit(2)
        out = crypto_proof(
            state["F"],
            state["A_hex"],
            state["A_int"],
            user,
            password,
            resp["s"],
            resp["B"],
        )
        print(json.dumps(out))
        return

    print("Use scripts/f1_ui_probe.sh (curl-only HTTP).", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
