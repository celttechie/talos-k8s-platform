# ADR 006: ArgoCD GitOps and the App-of-Apps Pattern

## Status
Accepted

## Context
Manual execution of `kubectl apply` or ad-hoc Helm installs leads to environment drift, untracked changes, and inconsistent cluster states. A continuous delivery mechanism is required to ensure Git remains the single source of truth for both cluster platform services and application workloads.

## Decision
We deploy **ArgoCD** following the **Root App-of-Apps Pattern**:
1. **Root Application**: A single root manifest (`gitops/bootstrap/root-application.yaml`) manages downstream `Application` resources representing platform modules (Cilium, Longhorn, Cert-Manager, External Secrets) and business workloads.
2. **Automated Drift Correction**: ArgoCD runs continuous reconciliation with automated synchronization and self-healing enabled.
3. **Decoupled Secrets**: No plaintext secrets are committed to Git; secrets are managed via Kubernetes secret references or External Secrets Operator.

## Consequences
- **Positive:** Total auditability of cluster state in Git history.
- **Positive:** Disaster recovery and cluster re-creation can be achieved with a single bootstrap command pointing to the repository.
- **Trade-off:** Requires all cluster modifications to follow the Git PR workflow rather than quick imperative `kubectl` edits.
