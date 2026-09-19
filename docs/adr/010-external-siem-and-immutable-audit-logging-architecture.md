# ADR 010: External SIEM Integration and Immutable Audit Logging Architecture

## Status
Accepted

## Context
Under DoD Impact Level 5 (IL5), NIST SP 800-53 (Controls AU-2, AU-3, AU-6, AU-9, AU-12), and DISA Kubernetes STIG (V-242402), all system events, kernel diagnostics, and administrative API requests must generate an immutable, tamper-resistant audit trail.

Retaining audit logs locally on ephemeral Kubernetes nodes introduces severe security risks: if an attacker compromises a node or gains cluster-admin privileges, local logs can be altered, truncated, or deleted to evade detection. Furthermore, because Talos Linux is an immutable, ephemeral OS without local persistent disk log partitions or interactive shells, system and kernel events must be exported off-node in real time.

## Decision
We establish a dedicated **External SIEM and Immutable Audit Logging Pipeline**:
1. **Node OS & Kernel Stream**: Configure Talos Linux declarative `machine.logging.destinations` to stream all OS, containerd, and kernel logs off-node via **RFC 5424 Syslog over TCP/TLS** (`tcp://<siem-host>:6514` with JSON lines formatting).
2. **Kubernetes API Server Audit Policy**: Configure Talos `cluster.apiServer.auditPolicy` with `RequestResponse` logging for security-sensitive API groups (`authorization.k8s.io`, `authentication.k8s.io`, `rbac.authorization.k8s.io`, `certificates.k8s.io`, and core `secrets`), streaming directly off-node to prevent local retention.
3. **Hypervisor & External SIEM Destination**: Define `SIEM_SYSLOG_ENDPOINT` in `target.env` pointing to a hardened external log receiver or dedicated SIEM vault container (e.g., Vector / Fluent Bit / Wazuh / OpenSearch) running on the hypervisor network (`192.168.9.110:6514`), decoupling log retention from cluster lifecycle.

## Consequences
- **Positive:** Guarantees non-repudiation and audit log integrity by preventing local log tampering or erasure during node compromise.
- **Positive:** Satisfies NIST 800-53 AU-6 / AU-12 and DISA STIG V-242402 compliance mandates for continuous centralized audit monitoring.
- **Positive:** Decouples log durability from ephemeral Talos node destruction and rolling upgrades.
- **Trade-off:** Introduces an operational dependency on network connectivity to the external SIEM receiver.
- **Trade-off:** Generates network egress traffic and requires appropriate SIEM storage capacity for full RequestResponse Kubernetes audit streams.
