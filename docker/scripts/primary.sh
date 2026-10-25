#!/bin/sh
set -eu
rm -f /tmp/primary-ready

cp /etc/postgresql/tls/server.crt /tmp/server.crt
cp /etc/postgresql/tls/server.key /tmp/server.key
chown postgres:postgres /tmp/server.crt /tmp/server.key
chmod 600 /tmp/server.key
docker-entrypoint.sh postgres -c ssl=on -c ssl_cert_file=/tmp/server.crt -c ssl_key_file=/tmp/server.key &
pid=$!
trap 'kill -TERM "$pid"; wait "$pid"' TERM INT
# TCP becomes available only after the entrypoint finishes initialization.
until pg_isready -h 127.0.0.1 -U primary_user -d main_db >/dev/null 2>&1; do
  kill -0 "$pid" || { wait "$pid"; exit 1; }
  sleep 1
done
rule='hostssl replication primary_user samenet scram-sha-256'
grep -qxF "$rule" "$PGDATA/pg_hba.conf" || printf '\n%s\n' "$rule" >> "$PGDATA/pg_hba.conf"
psql -v ON_ERROR_STOP=1 -U primary_user -d main_db -c 'SELECT pg_reload_conf();'
# Pass the password through psql variables so quotes cannot break the SQL.
replica_password=$(cat /run/secrets/postgres_replica_password)
psql -v ON_ERROR_STOP=1 -U primary_user -d main_db -v password="$replica_password" <<'SQL'
SELECT 'CREATE ROLE replica_user LOGIN' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'replica_user') \gexec
ALTER ROLE replica_user PASSWORD :'password';
SQL
touch /tmp/primary-ready
wait "$pid"
