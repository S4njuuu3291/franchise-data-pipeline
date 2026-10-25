#!/bin/sh
set -eu

export PGPASSWORD="$(cat /run/secrets/postgres_primary_password)"
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  # Clone into a staging directory; failed backups never look initialized.
  staging="$PGDATA/.basebackup"
  mkdir -p "$staging"
  find "$staging" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  pg_basebackup -d 'host=postgres-primary port=5432 user=primary_user sslmode=require' \
    -D "$staging" -v -P -R -X stream
  find "$staging" -mindepth 1 -maxdepth 1 -exec mv {} "$PGDATA/" \;
  rmdir "$staging"
fi
unset PGPASSWORD
test -f "$PGDATA/standby.signal"
cp /etc/postgresql/tls/server.crt /tmp/server.crt
cp /etc/postgresql/tls/server.key /tmp/server.key
chown postgres:postgres /tmp/server.crt /tmp/server.key
chmod 600 /tmp/server.key
chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"
exec su-exec postgres postgres -c ssl=on -c ssl_cert_file=/tmp/server.crt -c ssl_key_file=/tmp/server.key
