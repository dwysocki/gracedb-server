#!/bin/bash
# Initialises the development environment at the start of a Claude Code on
# the web session. Starts PostgreSQL, clones the sibling gracedb-helm-charts
# repository if absent, and — when the host kernel supports it — creates (or
# reattaches to) a k3d cluster so that kubectl and helm are ready to use.
# In gVisor environments (Claude Code web) it starts Podman and memcached
# instead, leaving the full container stack to `docker compose up`.
# No-ops when run outside a Claude Code remote environment.
set -euo pipefail

[[ "${CLAUDE_CODE_REMOTE:-}" != "true" ]] && exit 0

# ---------------------------------------------------------------------------
# Detect gVisor (runsc) sandbox. k3d / k3s / Docker daemon all require kernel
# APIs that gVisor does not expose. In gVisor we fall back to Podman +
# host-networking containers instead.
# ---------------------------------------------------------------------------
if grep -qi "gvisor\|runsc" /proc/version 2>/dev/null || \
   [[ "$(hostname)" == "runsc" ]]; then
    GVISOR=true
else
    GVISOR=false
fi

echo "=== SessionStart: services ==="
service postgresql start 2>/dev/null || true

echo "=== SessionStart: sibling helm repo ==="
if [[ ! -d /workspace/gracedb-helm-charts ]]; then
    git clone --depth 50 "${SIBLING_HELM_REPO}" /workspace/gracedb-helm-charts || {
        echo "WARN: could not clone helm-charts repo; k8s tasks will not work"
    }
fi

if [[ "${GVISOR}" == "true" ]]; then
    echo "=== SessionStart: gVisor detected — using Podman instead of k3d ==="

    # Start Podman's Docker-compatible API socket so docker / docker compose work.
    if [[ ! -S /var/run/docker.sock ]]; then
        podman system service --time=0 unix:///var/run/docker.sock &
        until [[ -S /var/run/docker.sock ]]; do sleep 1; done
        echo "Podman socket ready."
    fi

    # Start memcached for the native runserver path. The full container stack
    # (postgres + memcached + gracedb) is available via `docker compose up`.
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q gracedb-memcached; then
        docker run -d --name gracedb-memcached --network=host \
            memcached:1.6 2>/dev/null || true
        echo "memcached started on 127.0.0.1:11211"
    else
        echo "memcached already running."
    fi

    cat <<'INFO'

Environment ready (gVisor / Podman mode):
  PostgreSQL : 127.0.0.1:5432  (native)
  Memcached  : 127.0.0.1:11211 (Podman container)
  Docker API : /var/run/docker.sock -> Podman

For bare runserver:
  export DJANGO_SETTINGS_MODULE=config.settings.container.dev
  export DJANGO_DOCKER_MEMCACHED_ADDR=127.0.0.1:11211
  # ... set remaining required env vars (see compose.yml for the full list)
  python manage.py runserver 0.0.0.0:8000

For the full containerised stack:
  docker compose up          # builds image on first run (~10 min)
  docker compose up --build  # rebuild after Dockerfile changes
App will be at http://localhost:8000  (admin: admin/admin)
INFO
    exit 0
fi

echo "=== SessionStart: k3d cluster ==="
if ! k3d cluster list 2>/dev/null | grep -q "^${K3D_CLUSTER_NAME}"; then
    k3d cluster create "${K3D_CLUSTER_NAME}" \
        --servers 1 --agents 0 \
        --port "8080:80@loadbalancer" \
        --port "8443:443@loadbalancer" \
        --k3s-arg "--disable=traefik@server:*" \
        --wait
fi
k3d kubeconfig merge "${K3D_CLUSTER_NAME}" --kubeconfig-merge-default >/dev/null
kubectl config use-context "k3d-${K3D_CLUSTER_NAME}" >/dev/null

echo "=== SessionStart: cluster info ==="
kubectl cluster-info
kubectl get nodes
exit 0
