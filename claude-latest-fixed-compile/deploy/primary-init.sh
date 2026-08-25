#!/bin/bash
# Prepares the primary for streaming replication (NFR 1.2 / 2.3).
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE ROLE $REPLICATION_USER WITH REPLICATION LOGIN PASSWORD '$REPLICATION_PASSWORD';
  SELECT pg_create_physical_replication_slot('oms_replica_slot');
EOSQL

cat >> "$PGDATA/postgresql.conf" <<-EOCONF
wal_level = replica
max_wal_senders = 8
max_replication_slots = 8
hot_standby = on
synchronous_commit = on
EOCONF

# Allow the replica to stream from anywhere on the compose network.
echo "host replication $REPLICATION_USER 0.0.0.0/0 scram-sha-256" >> "$PGDATA/pg_hba.conf"
