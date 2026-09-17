# ADR 005: Longhorn Distributed Block Storage Architecture

## Status
Accepted

## Context
Stateful applications (such as databases and message queues) running on multi-node Kubernetes clusters require persistent volume storage that survives individual node reboots or failures. Local hostPath volumes pin pods to single VMs, preventing dynamic re-scheduling and high-availability failover.

## Decision
We implement **Longhorn CSI** as our primary distributed block storage engine:
1. **Dedicated Storage Disks**: Each Talos worker VM attaches a dedicated secondary virtual disk (`/dev/vdb`), partitioned and managed exclusively by Longhorn.
2. **Synchronous Block Replication**: Longhorn replicates volume data across multiple worker nodes (replicas = 2), ensuring zero data loss if a single worker node crashes.
3. **CSI Snapshots & Dynamic Expansion**: Supports Kubernetes standard `VolumeSnapshot` and online PVC resize operations.

## Consequences
- **Positive:** Enables true stateful high availability for databases (e.g. CloudNativePG).
- **Positive:** Native lightweight UI for monitoring volume health, replica rebuilds, and disk pressure.
- **Trade-off:** Longhorn replication incurs disk I/O and network bandwidth overhead across worker nodes.
