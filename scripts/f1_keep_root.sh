#!/bin/sh
# Started by the Airties launcher from the opt volume. Restores SSH root
# when an upgrade has replaced the overlay, then stays running so the
# launcher does not respawn it. The password files live beside this script
# on the router and are not in the repo.

DIR=/airties-edge/genesis
[ -f "$DIR/shadow" ] || exit 0
n=0
while [ ! -f /etc/shadow ]; do
	n=$((n + 1))
	[ "$n" -gt 30 ] && exit 0
	sleep 2
done
ok=1
grep -q '^root:\$6\$' /etc/shadow || ok=0
grep -qx '/bin/sh' /etc/shells || ok=0
en=$(uci -q get dropbear.@dropbear[0].enable || true)
[ "$en" = "1" ] || ok=0
if [ "$ok" -eq 0 ]; then
	cp "$DIR/shadow" /etc/shadow
	cp "$DIR/passwd" /etc/passwd
	cp "$DIR/shells" /etc/shells
	mkdir -p /etc/config
	cp "$DIR/dropbear" /etc/config/dropbear
	chmod 600 /etc/shadow /etc/config/dropbear
	chmod 644 /etc/passwd /etc/shells
	if [ -x /etc/init.d/dropbear ]; then
		/etc/init.d/dropbear enable
		/etc/init.d/dropbear restart
	fi
fi
if [ -n "$KEEP_ROOT_ONCE" ]; then
	exit 0
fi
while true; do
	sleep 3600
done
