#!/bin/sh
set -e
alembic upgrade head
if [ "${SEED_DEMO:-false}" = "true" ]; then
  python -m app.seed || true   # bo'sh bazada demo ma'lumot; allaqachon bo'lsa o'tkazib yuboradi
else
  python -m app.bootstrap
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
