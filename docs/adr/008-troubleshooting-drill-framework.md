# ADR 008: Interactive Troubleshooting Fault Injection Engine and Diagnostic Framework

## Status
Accepted

## Context
Practicing Kubernetes operations, incident response, and troubleshooting requires realistic, repeatable failure scenarios without permanently damaging the cluster configuration or leaving residual corrupted state.

## Decision
We implement a dedicated **Drill Manager CLI** (`scripts/drill_manager.py`) paired with a structured **4-Phase Diagnostic Framework** (`Detect -> Isolate -> Root Cause -> Remediate`):
1. **Cataloged Scenarios**: Modular scenarios covering Compute (OOM, CPU throttling, probe failures), Networking (DNS loss, CiliumNetworkPolicy drops, port/selector mismatches), and Storage (pending PVC, multi-attach locks, replica loss).
2. **Automated Injection & Healing**: Each scenario provides an idempotent `inject()` method that introduces the failure and a corresponding `heal()` method that returns the cluster to a verified clean baseline.
3. **Structured Runbooks**: Detailed documentation in `docs/troubleshooting-drills/` walking engineers through symptoms, diagnostic commands, root cause analysis, and remediation steps.

## Consequences
- **Positive:** Repeatable, safe failure simulation for training, interview preparation, and operational drills.
- **Positive:** Automated verification tests ensure all drill scenarios remain functional across platform upgrades.
- **Trade-off:** Requires maintaining drill manifests and healing logic in sync with workload and platform changes.
