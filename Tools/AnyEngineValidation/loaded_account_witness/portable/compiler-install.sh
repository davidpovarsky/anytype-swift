#!/bin/sh
# Exact acquired APK files only; Docker network is none. No compiler invocation builds code.
set -eu
umask 022
test "$(cat /etc/alpine-release)" = "3.24.4"
test "$(apk --print-arch)" = "aarch64"
test "$(sha256sum /lib/apk/db/installed | cut -d ' ' -f 1)" = "da766c29d2a171e8b2688c8eb215f47a514023a788775a9b6a42a27875d14e3c"
mkdir /out/keys-before /out/keys-after /out/tool-versions
cp /etc/apk/keys/*.pub /out/keys-before/
cp /lib/apk/db/installed /out/installed-before.txt
printf 'verify-same-apks\n' >> /out/phases.txt
apk --no-network verify /inputs/packages/*.apk > /out/verify.log 2>&1
printf 'offline-install\n' >> /out/phases.txt
apk --no-network add /inputs/packages/*.apk > /out/install.log 2>&1
cp /lib/apk/db/installed /out/installed-after.txt
cp /etc/apk/keys/*.pub /out/keys-after/
printf 'tool-observations\n' >> /out/phases.txt
for tool in gcc g++ cc c++ ld as ar ranlib; do
  path="$(command -v "$tool")"
  real="$(readlink -f "$path")"
  test -f "$real" && test -x "$real"
  printf '%s\t%s\t%s\t%s\t%s\n' "$tool" "$path" "$real" "$(sha256sum "$real" | cut -d ' ' -f 1)" "$(stat -c '%a:%u:%g:%s' "$real")" >> /out/tools.tsv
  "$path" --version > "/out/tool-versions/$tool.txt" 2>&1
done
gcc -dumpmachine > /out/gcc-target.txt
g++ -dumpmachine > /out/gpp-target.txt
test "$(cat /out/gcc-target.txt)" = "aarch64-alpine-linux-musl"
test "$(cat /out/gpp-target.txt)" = "aarch64-alpine-linux-musl"
for tool in cc1 cc1plus collect2 lto1 lto-wrapper; do
  path="$(gcc -print-prog-name="$tool")"
  test -f "$path" && test -x "$path"
  real="$(readlink -f "$path")"
  printf '%s\t%s\t%s\t%s\t%s\n' "$tool" "$path" "$real" "$(sha256sum "$real" | cut -d ' ' -f 1)" "$(stat -c '%a:%u:%g:%s' "$real")" >> /out/compiler-support.tsv
done
printf 'installation-complete\n' >> /out/phases.txt
