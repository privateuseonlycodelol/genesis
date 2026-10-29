# CUPS UDP 631 browse listener: pinned 2.2.10 source review (2026-10-29)

## Question

The live device answers no UDP 631 probes (one empty datagram, one benign CUPS browse advertisement; see `findings/tried.md`). Does the CUPS scheduler itself listen for browse packets on UDP 631?

## Source reviewed (VERIFIED by file listing and grep)

- Pinned commit `25b2338346ef3abbb93ea88476887cba7b2b86f8` (tag `v2.2.10`), fetched read-only from the public repo.
- The tree API lists 70 `scheduler/` files. No `browse.c` or `browsing.c` exists at this commit (direct fetches returned 404).
- `scheduler/dirsvc.c` (`artifacts/management/cups-source-v2.2.10/dirsvc.c`, sha256 recorded when fetched) handles browsing only through `BROWSE_DNSSD`, `BROWSE_LPD` and `BROWSE_SMB`. It contains no `recvfrom`, `sendto`, `SOCK_DGRAM` or UDP reference.
- `scheduler/listen.c` contains no `SOCK_DGRAM` reference.

## Derived

- **DERIVED:** The pinned 2.2.10 `cupsd` has no UDP 631 browse listener. CUPS 2.2.x moved UDP browse handling out of the scheduler.
- **DERIVED:** The UDP 631 open|filtered result is therefore more likely a separate listener, such as the `cups-browsed` daemon from the `cups-filters` package, than `cupsd`.
- **UNKNOWN:** Whether the device ships `cups-browsed`, and its version. Nothing offline shows it.

## Not shown

- No live test identified which process listens on UDP 631.
- The device's `cupsd` version is only read from its HTML page (`Forbidden - CUPS v2.2.10`) and is unverified.
- Advisories on `cups-browsed` are not checked against any version here, because no version is known.

## Next

1. Confirm the device package set and `cups-browsed` version from the 23.1.b rootfs (GPL source request, `findings/f1-gpl-source-request-2026-10-29.md`).
2. Only after a version is confirmed, compare it with published `cups-browsed` advisories. No packets are to be sent to the device for this step.
