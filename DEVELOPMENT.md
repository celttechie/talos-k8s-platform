# Developer & Workflow Guide

> [!NOTE]
> **Project Status: Beta (Feature Complete / In Verification)**
> All core platform components (M1–M6) are fully implemented. The repository is actively in testing, preflight diagnostics, and troubleshooting drill verification.

This guide establishes the local development workflow, quality assurance standards, environment diagnostics, and step-by-step commands for the **Talos Kubernetes Platform**.

---

## 1. Environment Assessment (`make doctor`)

Before executing any provisioning stages, run the automated environment doctor to verify your local tools, binary versions, and security configurations:

```bash
make doctor
```

### Tooling Prerequisites Checklist

| Binary | Minimum Version | Installation / Upgrade Reference | Purpose |
| :--- | :--- | :--- | :--- |
| **Terraform / OpenTofu** | $\ge$ 1.5.0 | `sudo snap install terraform --classic` or apt | Hypervisor & VM Infrastructure-as-Code |
| **Talos CLI (`talosctl`)** | $\ge$ 1.8.0 | `curl -sL https://talos.dev/install \| sh` | Talos OS mTLS API & cluster operations |
| **Kubernetes CLI (`kubectl`)** | $\ge$ 1.30.0 | `curl -LO "https://dl.k8s.io/release/.../bin/linux/amd64/kubectl"` | Upstream cluster management |
| **Helm CLI** | $\ge$ 3.14.0 | `curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 \| bash` | Platform charts & packaging |
| **Cilium CLI** | $\ge$ 0.16.0 | `CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt); curl -L --fail --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz` | eBPF connectivity testing & Hubble |
| **GitHub CLI (`gh`)** | $\ge$ 2.40.0 | `sudo apt install gh` | Milestones, PRs, and Issue tracking |
| **Pre-Commit** | $\ge$ 3.6.0 | `pip install pre-commit` | Git commit quality gates & secret scanning |

---

## 2. Pre-Commit Quality Guardrails

To prevent accidental secret leaks (`talosconfig`, `kubeconfig`, private keys) and enforce clean code standards, install the pre-commit hooks:

```bash
pre-commit install
make lint
```

### Registered Checks:
- **Gitleaks / Secret Scanning**: Blocks unencrypted secrets, certificates, and credentials.
- **Terraform Formatting**: Enforces `terraform fmt -check`.
- **YAML / Markdown Linting**: Enforces schema validity and documentation hygiene.

---

## 3. Git Workflow & Branch Conventions

We follow a strict PR-driven workflow:

1. **Branching Model**:
   - `main`: Protected production-ready branch.
   - `feat/<feature-name>`: New infrastructure or platform capabilities (e.g., `feat/stage1-sandbox-vm`, `feat/cilium-ebpf`).
   - `fix/<fix-name>`: Bug fixes or configuration tuning.
   - `docs/<doc-name>`: Documentation or ADR additions.
2. **Commit Standard**: Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` New features or infrastructure resources.
   - `fix:` Bug fixes or configuration corrections.
   - `docs:` Documentation or ADR additions.
   - `chore:` Maintenance, dependency updates, or pre-commit adjustments.

---

## 4. Multi-Stage Deployment Lifecycle

Infrastructure provisioning is structured into sequential, independently verifiable stages:

```bash
# -------------------------------------------------------------
# Stage 0: Nested Sandbox Hypervisor (L1 VM) - Optional
# -------------------------------------------------------------
make stage0-init
make stage0-plan
make stage0-apply
make verify-stage0

# -------------------------------------------------------------
# Stage 1: Talos Downstream Cluster (L2 VMs)
# -------------------------------------------------------------
make stage1-init
make stage1-plan
make stage1-apply
make verify-stage1

# -------------------------------------------------------------
# Stage 2: Talos OS & Control Plane Bootstrapping
# -------------------------------------------------------------
make talos-gen-config
make talos-bootstrap
make talos-kubeconfig
make talos-health
make verify-stage2

# -------------------------------------------------------------
# Stage 3: Platform Services (Cilium eBPF & Longhorn Storage)
# -------------------------------------------------------------
make cilium-install
make longhorn-install
make verify-stage3

# -------------------------------------------------------------
# Stage 4: GitOps Delivery & Training Workloads
# -------------------------------------------------------------
make gitops-bootstrap
make workload-install
make verify-stage4

# -------------------------------------------------------------
# Stage 5: Observability (Prometheus, Grafana & Hubble)
# -------------------------------------------------------------
make monitoring-install
make verify-stage5

# -------------------------------------------------------------
# Fault Injection Drills & Disaster Recovery
# -------------------------------------------------------------
make drill-list
make drill-inject SCENARIO=comp-oom-killed
make drill-verify SCENARIO=comp-oom-killed
make drill-heal SCENARIO=comp-oom-killed
```

---

## 5. Milestone Verification Test Suites

Each milestone contains an automated test harness to validate syntax, manifest schemas, and configuration integrity:

```bash
make test-m1   # Milestone 1: Terraform modules & virtualization schemas
make test-m2   # Milestone 2: Talos config generator & machine patches
make test-m3   # Milestone 3: Cilium CNI eBPF & Longhorn storage values
make test-m4   # Milestone 4: GitOps root-app & microservice workload manifests
make test-m5   # Milestone 5: Drill manager CLI & troubleshooting scenarios
make test-m6   # Milestone 6: Prometheus rules, alert thresholds & Grafana dashboards
```
