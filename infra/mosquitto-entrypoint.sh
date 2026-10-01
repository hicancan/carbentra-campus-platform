#!/bin/sh
set -eu
# File-backed Compose secrets retain host UID/mode. Copy only this service's
# secrets into its private tmpfs, as the existing non-root broker identity.
umask 077
private=/tmp/mqtt-private
mkdir -p "$private"
chmod 0700 "$private"
for name in mqtt_ca mqtt_server_certificate mqtt_server_key mqtt_acl; do
    [ -r "/run/secrets/$name" ] || { echo "Required broker secret is unreadable: $name" >&2; exit 1; }
    cat "/run/secrets/$name" > "$private/$name"
    chmod 0600 "$private/$name"
done
exec mosquitto -c /mosquitto/config/mosquitto.conf
