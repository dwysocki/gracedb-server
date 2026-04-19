#!/bin/bash
# Reports the state of the dev environment. Not an assertion — just observation.
echo "--- tools ---"
for t in python pip docker k3d kubectl helm psql memcached; do
    printf "%-12s " "$t"
    command -v "$t" >/dev/null && "$t" --version 2>&1 | head -1 || echo "MISSING"
done
echo "--- services ---"
pg_isready -h localhost -p 5432 || true
docker ps --format 'table {{.Names}}\t{{.Status}}' | head -20
k3d cluster list || true
echo "--- sibling repo ---"
[[ -d /workspace/gracedb-helm-charts ]] && echo "helm-charts repo: present" || echo "helm-charts repo: MISSING"
echo "--- django settings ---"
echo "DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-NOT SET}"
