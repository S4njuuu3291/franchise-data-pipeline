#!/bin/sh
set -eu

export GRAFANA_DB_PASSWORD="$(cat /run/secrets/gx_metadata_password)"

exec /run.sh "$@"
