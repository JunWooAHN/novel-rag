#!/bin/sh
# Continue the unchanged official YAGO archive on H200 Storage after SSH disconnects.
set -u

tool=/home/work/novel-toy-tune/tools/yago_storage/20260928
base=/home/work/novel-toy-tune
original="$base/sources/original/yago/4.6"
log="$tool/server-fetch.log"
status="$tool/server-fetch.status"
exit_file="$tool/server-fetch.exit"
pid_file="$tool/server-fetch.pid"

cd "$tool" || exit 2
exec >> "$log" 2>&1
printf '%s\n' "$$" > "$pid_file"
printf '%s\n' running > "$status"
printf 'START %s pid=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$$"

finish() {
  result=$1
  if [ "$result" -eq 0 ]; then
    printf '%s\n' complete > "$status"
  else
    printf '%s\n' failed > "$status"
  fi
  printf '%s\n' "$result" > "$exit_file"
  printf 'END %s exit=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$result"
  exit "$result"
}

python3 fetch_original.py preflight --storage-base "$base" --root "$original" \
  --expected-mount-target "$base" || finish 2

attempt=1
while [ "$attempt" -le 3 ]; do
  printf 'FETCH attempt=%s %s\n' "$attempt" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 -u fetch_original.py fetch --storage-base "$base" --root "$original" \
    --expected-mount-target "$base"
  result=$?
  if [ "$result" -eq 0 ]; then
    break
  fi
  if ! tail -n 5 "$log" | grep -Eq 'Resource temporarily unavailable|download interrupted after 3 attempts|timed out|URLError'; then
    finish "$result"
  fi
  if [ "$attempt" -eq 3 ]; then
    finish "$result"
  fi
  attempt=$((attempt + 1))
  sleep 15
done

printf 'VERIFY %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 -u fetch_original.py verify --storage-base "$base" --root "$original" \
  --expected-mount-target "$base"
result=$?
finish "$result"
