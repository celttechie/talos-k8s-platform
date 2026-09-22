#!/usr/bin/env bash
# ==============================================================================
# Talos Cluster Machine Configuration Generator
# ==============================================================================
# Generates declarative Talos machine configs (controlplane.yaml, worker.yaml)
# and admin client credentials (talosconfig) with Cilium eBPF and Longhorn patches.
# ==============================================================================

set -euo pipefail

# Script directory resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Configuration defaults
CLUSTER_NAME="${CLUSTER_NAME:-talos-k8s-platform}"
if [[ -z "${CONTROL_PLANE_IP:-}" ]]; then
    if [[ -d "${REPO_ROOT}/terraform/environments/01-talos-cluster" ]]; then
        DETECTED_CP_IP=$(python3 -c '
import json, os, subprocess
try:
    repo = os.environ.get("REPO_ROOT", ".")
    res = subprocess.run(["terraform", f"-chdir={repo}/terraform/environments/01-talos-cluster", "output", "-json"], capture_output=True, text=True)
    data = json.loads(res.stdout)
    print(data.get("cluster_endpoints", {}).get("value", {}).get("controlplane_ip", ""))
except Exception:
    print("")
' 2>/dev/null || true)
        if [[ -n "${DETECTED_CP_IP}" ]]; then
            CONTROL_PLANE_IP="${DETECTED_CP_IP}"
        fi
    fi
fi
CONTROL_PLANE_IP="${CONTROL_PLANE_IP:-192.168.122.10}"
CONTROL_PLANE_PORT="${CONTROL_PLANE_PORT:-6443}"
CONTROL_PLANE_ENDPOINT="${CONTROL_PLANE_ENDPOINT:-https://${CONTROL_PLANE_IP}:${CONTROL_PLANE_PORT}}"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/talos}"
PATCHES_DIR="${OUTPUT_DIR}/patches"
TALOS_VERSION="${TALOS_VERSION:-v1.8}"
KUBERNETES_VERSION="${KUBERNETES_VERSION:-1.31.0}"
SECRETS_FILE="${OUTPUT_DIR}/secrets.yaml"

# Colors
GREEN="\033[32m"
BLUE="\033[36m"
YELLOW="\033[33m"
RED="\033[31m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "\n${BOLD}${BLUE}==============================================================================${RESET}"
echo -e "${BOLD}${BLUE}     Talos Linux Machine Configuration Generator                              ${RESET}"
echo -e "${BOLD}${BLUE}==============================================================================${RESET}\n"

# Verify talosctl binary
if ! command -v talosctl &>/dev/null; then
    echo -e "${RED}Error: talosctl is not installed or not found in PATH.${RESET}"
    echo -e "Install with: curl -sL https://talos.dev/install | sh"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}" "${PATCHES_DIR}"

echo -e "${BLUE}Cluster Name:${RESET}             ${BOLD}${CLUSTER_NAME}${RESET}"
echo -e "${BLUE}Control Plane Endpoint:${RESET}   ${BOLD}${CONTROL_PLANE_ENDPOINT}${RESET}"
echo -e "${BLUE}Talos Version:${RESET}            ${BOLD}${TALOS_VERSION}${RESET}"
echo -e "${BLUE}Kubernetes Version:${RESET}       ${BOLD}${KUBERNETES_VERSION}${RESET}"
echo -e "${BLUE}Output Directory:${RESET}         ${OUTPUT_DIR}"

# Step 1: Manage Secret Bundle
if [[ ! -f "${SECRETS_FILE}" ]]; then
    echo -e "\n${GREEN}===> Generating new master secret bundle: ${SECRETS_FILE}...${RESET}"
    talosctl gen secrets -o "${SECRETS_FILE}"
else
    echo -e "\n${YELLOW}===> Reusing existing master secret bundle: ${SECRETS_FILE}${RESET}"
fi

# Step 2: Generate Configs with Patches
echo -e "\n${GREEN}===> Generating declarative machine configurations with patches...${RESET}"

PATCH_ARGS=()
if [[ -f "${PATCHES_DIR}/cilium.yaml" ]]; then
    echo -e "  ✓ Applying Cilium CNI patch (all nodes): ${PATCHES_DIR}/cilium.yaml"
    PATCH_ARGS+=(--config-patch "@${PATCHES_DIR}/cilium.yaml")
fi

if [[ -f "${PATCHES_DIR}/longhorn-storage.yaml" ]]; then
    echo -e "  ✓ Applying Longhorn Storage patch (workers only): ${PATCHES_DIR}/longhorn-storage.yaml"
    PATCH_ARGS+=(--config-patch-worker "@${PATCHES_DIR}/longhorn-storage.yaml")
fi

talosctl gen config "${CLUSTER_NAME}" "${CONTROL_PLANE_ENDPOINT}" \
    --with-secrets "${SECRETS_FILE}" \
    --output-dir "${OUTPUT_DIR}" \
    --talos-version "${TALOS_VERSION}" \
    --kubernetes-version "${KUBERNETES_VERSION}" \
    "${PATCH_ARGS[@]}" \
    --force


# Step 3: Validate generated configs
echo -e "\n${GREEN}===> Validating generated machine configurations...${RESET}"
talosctl validate -c "${OUTPUT_DIR}/controlplane.yaml" -m metal
echo -e "  ✓ ${BOLD}controlplane.yaml${RESET} validation passed."

talosctl validate -c "${OUTPUT_DIR}/worker.yaml" -m metal
echo -e "  ✓ ${BOLD}worker.yaml${RESET} validation passed."

echo -e "\n${BOLD}${GREEN}✓ Machine configurations successfully generated and validated!${RESET}\n"
echo -e "${BOLD}Generated Artifacts in ${OUTPUT_DIR}:${RESET}"
echo -e "  • ${BOLD}controlplane.yaml${RESET} - Machine config for talos-cp-01"
echo -e "  • ${BOLD}worker.yaml${RESET}       - Machine config for worker nodes (with storage disk /dev/vdb)"
echo -e "  • ${BOLD}talosconfig${RESET}       - mTLS admin client configuration"
echo -e "  • ${BOLD}secrets.yaml${RESET}      - Master PKI & encryption secrets (git-ignored)"

echo -e "\n${BOLD}Next Lifecycle Steps:${RESET}"
echo -e "  1. Apply config to Control Plane: ${BLUE}talosctl apply-config --insecure -n <cp-ip> --file talos/controlplane.yaml${RESET}"
echo -e "  2. Apply config to Workers:       ${BLUE}talosctl apply-config --insecure -n <worker-ip> --file talos/worker.yaml${RESET}"
echo -e "  3. Bootstrap cluster:             ${BLUE}make talos-bootstrap${RESET}"
echo -e "  4. Retrieve kubeconfig:           ${BLUE}make talos-kubeconfig${RESET}\n"
