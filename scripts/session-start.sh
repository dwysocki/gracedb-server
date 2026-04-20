#!/bin/bash
# Initialises the k3d-based development environment at the start of a
# Claude Code on the web session. Starts PostgreSQL, clones the sibling
# gracedb-helm-charts repository if absent, and creates (or reattaches to)
# a k3d cluster so that kubectl and helm are ready to use.
# No-ops when run outside a Claude Code remote environment.
set -euo pipefail

[[ "${CLAUDE_CODE_REMOTE:-}" != "true" ]] && exit 0

echo "=== SessionStart: services ==="
service postgresql start 2>/dev/null || true

echo "=== SessionStart: sibling helm repo ==="
if [[ ! -d /workspace/gracedb-helm-charts ]]; then
    git clone --depth 50 "${SIBLING_HELM_REPO}" /workspace/gracedb-helm-charts || {
        echo "WARN: could not clone helm-charts repo; k8s tasks will not work"
    }
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
