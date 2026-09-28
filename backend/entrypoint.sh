#!/bin/sh
set -eu

python - <<'PY'
import os
import time

import psycopg

settings = {
    "dbname": os.environ.get("POSTGRES_DB", "comments"),
    "user": os.environ.get("POSTGRES_USER", "comments"),
    "password": os.environ.get("POSTGRES_PASSWORD", "comments"),
    "host": os.environ.get("POSTGRES_HOST", "db"),
    "port": os.environ.get("POSTGRES_PORT", "5432"),
}

for attempt in range(30):
    try:
        with psycopg.connect(**settings):
            break
    except psycopg.OperationalError:
        if attempt == 29:
            raise
        time.sleep(2)
PY

if [ "${RUN_MIGRATIONS:-True}" = "True" ]; then
    python manage.py migrate --noinput
fi
exec "$@"
