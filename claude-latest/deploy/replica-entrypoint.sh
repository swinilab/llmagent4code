#!/bin/bash
# Bootstraps a hot-standby from the primary via pg_basebackup (NFR 1.2).
set -euo pipefail

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "replica: waiting for primary to accept connections..."
  until pg_isready -h "$PRIMARY_HOST" -U "$REPLICATION_USER" -q; do
    sleep 1
  done

  echo "replica: taking base backup from $PRIMARY_HOST"
  rm -rf "${PGDATA:?}"/*
  PGPASSWORD="$REPLICATION_PASSWORD" pg_basebackup \
    --host="$PRIMARY_HOST" \
    --username="$REPLICATION_USER" \
    --pgdata="$PGDATA" \
    --wal-method=stream \
    --slot=oms_replica_slot \
    --write-recovery-conf \
    --checkpoint=fast \
    --progress --verbose

  chmod 0700 "$PGDATA"
  echo "replica: base backup complete; starting as hot standby"
fi

exec postgres
