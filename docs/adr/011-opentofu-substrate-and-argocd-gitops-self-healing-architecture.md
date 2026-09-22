# ADR 011: OpenTofu Substrate & Declarative ArgoCD GitOps Self-Healing Architecture

## Status
Accepted (Supersedes procedural script orchestration across Stages 2–5)

## Context
Initial iterations of the platform used Python scripts and `Makefile` targets to imperatively execute `talosctl`, `helm`, and `kubectl` commands sequentially for bootstrapping and installing platform services (Cilium, Longhorn, ArgoCD, Observability, Workloads). While functional for early prototyping, this approach has key limitations:
1. **No Automated Drift Correction**: If an in-cluster resource or node configuration is modified or deleted, the procedural scripts cannot automatically detect or repair the drift.
2. **Procedural vs. Declarative Conflict**: In-cluster Helm installations run imperatively from developer workstations, requiring active internet access at runtime and bypassing declarative state tracking.
3. **Air-Gap / Defense Unicorns Alignment**: Preparing for mission environments (Defense Unicorns Zarf / UDS) requires a strict separation of concerns: OpenTofu manages the bare-metal / VM hardware substrate and Talos OS lifecycle, while in-cluster platform components and applications are delivered and continuously reconciled via declarative GitOps and self-contained packages.

## Decision
We establish a **Two-Tier Architecture**:

### 1. Substrate Layer: OpenTofu (Stages 0–2)
- **Hypervisor & VM Topology (Stages 0 & 1)**: OpenTofu provisions the sandbox hypervisor and downstream Talos VMs via the `dmacvicar/libvirt` provider.
- **Talos Machine Configs, PKI Secrets & Bootstrapping (Stage 2)**: Transition from Python/Bash script generation to the official `siderolabs/talos` OpenTofu provider. OpenTofu declaratively defines PKI secrets, applies machine configurations over mTLS, bootstraps etcd quorum, and outputs the administrative `kubeconfig` directly into state.
- **GitOps Bootstrap (Stage 2/3 handoff)**: OpenTofu applies the minimal initial ArgoCD controller or ArgoCD is deployed as the bootstrap GitOps engine.

### 2. Platform Delivery & Self-Healing Layer: ArgoCD GitOps (Stages 3–5)
- **Root App-of-Apps Pattern**: All platform services (Cilium eBPF CNI, Longhorn CSI, External Secrets Operator, Observability Stack) and application workloads are managed as declarative ArgoCD `Application` resources under `gitops/bootstrap/root-application.yaml`.
- **Automated Self-Healing**: All ArgoCD applications have automated synchronization enabled with `selfHeal: true` and `prune: true`. Any manual modification, deletion, or drift inside the cluster is automatically corrected back to the desired Git state within seconds without running manual scripts.
- **Air-Gap Readiness**: Platform manifests and charts are stored declaratively in the repository, enabling seamless migration to internal container registries, Zarf packages, and UDS bundles.

## Consequences
- **Positive:** Total declarative convergence across the entire lifecycle: OpenTofu reconciles infrastructure substrate; ArgoCD reconciles in-cluster software.
- **Positive:** Zero manual intervention required for drift recovery: deleting a deployment or service triggers immediate automatic restoration by ArgoCD.
- **Positive:** Full alignment with Defense Unicorns Zarf/UDS air-gapped platform delivery standards.
- **Trade-off:** In-cluster component updates must be committed to Git rather than applied imperatively via `make <service>-install`.
