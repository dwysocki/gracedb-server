#!/bin/bash
# Initialises the development environment at the start of a Claude Code on
# the web session. Starts PostgreSQL, clones the sibling gracedb-helm-charts
# repository if absent, and — when the host kernel supports it — creates (or
# reattaches to) a k3d cluster so that kubectl and helm are ready to use.
# No-ops when run outside a Claude Code remote environment.
set -euo pipefail

[[ "${CLAUDE_CODE_REMOTE:-}" != "true" ]] && exit 0

# ---------------------------------------------------------------------------
# Detect gVisor (runsc) sandbox — reported via /proc/version on gVisor hosts.
# k3d / k3s / Docker daemon all require kernel APIs that gVisor does not expose
# (cgroups rootfs, overlay filesystem, iptables/nftables).  Skip the cluster
# step and warn instead of failing hard.
# ---------------------------------------------------------------------------
if grep -qi "gvisor\|runsc" /proc/version 2>/dev/null || \
   [[ "$(uname -r)" == *"+"* && "$(hostname)" == "runsc" ]]; then
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

echo "=== SessionStart: k3d cluster ==="
if [[ "${GVISOR}" == "true" ]]; then
    cat <<'WARN'
*** gVisor sandbox detected ***
Docker daemon, k3d, and k3s are not supported in this environment.
Kernel limitations:
  - iptables/nftables unavailable  → Docker daemon cannot start
  - overlay filesystem unsupported → containerd native snapshotter required
  - cgroup rootfs not exposed      → kubelet ContainerManager fails
Falling back to direct Django runserver for development.
WARN
    exit 0
fi

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
