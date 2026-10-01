#!/bin/sh
set -eu
: "${CARBENTRA_DEMO_HOST:?An explicit DNS host is required}"
case "$CARBENTRA_DEMO_HOST" in *[!a-zA-Z0-9.-]*|'') echo 'Invalid demo DNS host' >&2; exit 1 ;; esac
# Substitute only the hostname, preserving nginx's runtime variables.
envsubst '${CARBENTRA_DEMO_HOST}' < /etc/carbentra/public-demo/nginx.conf.template > /tmp/nginx.conf
nginx -t -c /tmp/nginx.conf
exec nginx -c /tmp/nginx.conf -g 'daemon off;'
