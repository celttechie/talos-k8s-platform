# ADR 009: Continuous Compliance and OSCAL Validation with Defense Unicorns Lula

## Status
Accepted

## Context
Deploying workloads in defense, intelligence, and regulated environments requires continuous verification against security baselines, specifically **DoD Impact Level 5 (IL5)**, **DISA Kubernetes STIG**, and **NIST SP 800-53 Rev 5**. Traditional compliance approaches rely on manual, point-in-time spreadsheets and audit screenshots that rapidly become stale, fail to provide automated regression testing, and cannot be evaluated prior to deployment.

We need a machine-readable, continuous compliance-as-code solution that:
1. Validates declarative configurations **shift-left** (in static YAML before deployment).
2. Verifies the **live cluster state** post-deployment against formal security controls.
3. Produces standardized **OSCAL (Open Security Controls Assessment Language)** artifacts for authorizing officials (AOs) and auditors.

## Decision
We adopt **Defense Unicorns Lula** as the compliance assessment engine for the platform:
1. **OSCAL Component Definitions**: Maintain declarative OSCAL models in `compliance/lula/oscal-component.yaml` mapping platform components (Talos OS, Kubernetes Control Plane, Cilium CNI, Longhorn CSI, and Kyverno admission controls) directly to DISA STIG rules (`V-242400`–`V-242460`) and NIST 800-53 controls.
2. **Dual-Phase Validation Architecture**:
   - **Shift-Left Static Evaluation (`make lula-validate-static`)**: Uses Lula's file/YAML and OPA Rego validation providers to inspect `talos/controlplane.yaml`, `gitops/platform/cilium/values.yaml`, and `gitops/apps/**/*.yaml` during pre-commit and CI/CD before any deployment occurs.
   - **Live Cluster Evaluation (`make lula-validate-live`)**: Uses Lula's Kubernetes provider to query the active API server, validating running container security contexts, WireGuard network mesh encryption, and storage encryption.
3. **Automated Assessment Output**: Generate structured `assessment-results.yaml` OSCAL documents and human-readable compliance matrices to provide continuous, verifiable audit evidence.

## Consequences
- **Positive:** Automates DISA STIG and DoD IL5 control verification directly within developer and CI/CD pipelines.
- **Positive:** Discovers security regressions and non-compliant YAML configurations before they reach hypervisors or clusters.
- **Positive:** Employs the NIST-standardized OSCAL data model, aligning directly with modern DoD software factory accreditation standards (e.g., Platform One, Big Bang).
- **Trade-off:** Requires authoring and maintaining OSCAL component definitions and Rego/Kube validation contracts alongside infrastructure and GitOps manifest updates.
