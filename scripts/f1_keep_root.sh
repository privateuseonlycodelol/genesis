#!/bin/sh
# Started by the Airties launcher from the opt volume. Restores root SSH
# when the live login settings no longer match the saved copies beside this
# script, then keeps checking. The password files stay on the router.

DIR=/airties-edge/genesis
[ -f "$DIR/shadow" ] || exit 0

root_field() {
	awk -F: -v f="$2" '/^root:/{print $f; exit}' "$1"
}

uci_get() {
	uci -q get "$1" 2>/dev/null || true
}

saved_opt() {
	awk -v k="$1" '
		$1 == "option" && $2 == k {
			v = $3
			gsub(/'\''/, "", v)
			gsub(/"/, "", v)
			print v
			exit
		}
	' "$DIR/dropbear"
}

off() {
	[ "$1" = "0" ] || [ "$1" = "off" ]
}

healthy() {
	[ -f /etc/shadow ] || return 1
	[ -f /etc/passwd ] || return 1
	[ -f /etc/shells ] || return 1
	saved=$(root_field "$DIR/shadow" 2)
	live=$(root_field /etc/shadow 2)
	[ -n "$saved" ] && [ "$saved" = "$live" ] || return 1
	want=$(root_field "$DIR/passwd" 7)
	[ -n "$want" ] || want=/bin/sh
	[ "$(root_field /etc/passwd 7)" = "$want" ] || return 1
	grep -qx '/bin/sh' /etc/shells || return 1
	[ "$(uci_get dropbear.@dropbear[0].enable)" = "1" ] || return 1
	off "$(uci_get dropbear.@dropbear[0].PasswordAuth)" && return 1
	off "$(uci_get dropbear.@dropbear[0].RootPasswordAuth)" && return 1
	off "$(uci_get dropbear.@dropbear[0].RootLogin)" && return 1
	return 0
}

put_file() {
	tmp=$1
	dest=$2
	mode=$3
	cp "$tmp" "$dest" && chmod "$mode" "$dest"
	rm -f "$tmp"
}

restore() {
	saved=$(root_field "$DIR/shadow" 2)
	if [ -n "$saved" ] && [ -f /etc/shadow ]; then
		if grep -q '^root:' /etc/shadow; then
			awk -F: -v h="$saved" 'BEGIN{OFS=":"} $1=="root"{$2=h} {print}' /etc/shadow > /tmp/shadow.keeproot \
				&& put_file /tmp/shadow.keeproot /etc/shadow 600
		else
			grep '^root:' "$DIR/shadow" >> /etc/shadow
			chmod 600 /etc/shadow
		fi
	fi
	want=$(root_field "$DIR/passwd" 7)
	[ -n "$want" ] || want=/bin/sh
	if [ -f /etc/passwd ]; then
		if grep -q '^root:' /etc/passwd; then
			awk -F: -v s="$want" 'BEGIN{OFS=":"} $1=="root"{$7=s} {print}' /etc/passwd > /tmp/passwd.keeproot \
				&& put_file /tmp/passwd.keeproot /etc/passwd 644
		else
			grep '^root:' "$DIR/passwd" >> /etc/passwd
			chmod 644 /etc/passwd
		fi
	fi
	if [ -f /etc/shells ]; then
		grep -qx '/bin/sh' /etc/shells || echo '/bin/sh' >> /etc/shells
	elif [ -f "$DIR/shells" ]; then
		cp "$DIR/shells" /etc/shells && chmod 644 /etc/shells
	fi
	if command -v uci >/dev/null 2>&1; then
		uci -q get dropbear.@dropbear[0] >/dev/null 2>&1 || uci -q add dropbear dropbear >/dev/null
		uci -q set dropbear.@dropbear[0].enable='1'
		pa=$(saved_opt PasswordAuth)
		[ -n "$pa" ] || pa=on
		ra=$(saved_opt RootPasswordAuth)
		[ -n "$ra" ] || ra=on
		rl=$(saved_opt RootLogin)
		[ -n "$rl" ] || rl=1
		port=$(saved_opt Port)
		[ -n "$port" ] || port=22
		iface=$(saved_opt Interface)
		uci -q set dropbear.@dropbear[0].PasswordAuth="$pa"
		uci -q set dropbear.@dropbear[0].RootPasswordAuth="$ra"
		uci -q set dropbear.@dropbear[0].RootLogin="$rl"
		uci -q set dropbear.@dropbear[0].Port="$port"
		[ -n "$iface" ] && uci -q set dropbear.@dropbear[0].Interface="$iface"
		uci -q commit dropbear
	fi
	if [ -x /etc/init.d/dropbear ]; then
		/etc/init.d/dropbear enable
		/etc/init.d/dropbear restart
	fi
}

if [ -n "$KEEP_ROOT_ONCE" ]; then
	n=0
	while [ ! -f /etc/shadow ]; do
		n=$((n + 1))
		[ "$n" -gt 30 ] && exit 1
		sleep 2
	done
	healthy || restore
	exit 0
fi

while true; do
	if [ -f /etc/shadow ]; then
		healthy || restore
	fi
	sleep 60
done
