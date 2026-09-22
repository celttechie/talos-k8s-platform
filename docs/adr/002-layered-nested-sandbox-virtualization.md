# ADR 002: Layered Nested Sandbox Virtualization

## Status
Accepted

## Context
Deploying multi-node Kubernetes clusters directly on a bare-metal hypervisor host creates environment contamination risks, makes full-system tear-downs difficult, and exposes the physical LAN to experimental DHCP/eBPF routing. To establish a production-grade VPC boundary while supporting safe local development on a single server (Dell Precision T5600), an isolation strategy is required.

## Decision
We implement a **Two-Stage Layered Sandbox Virtualization Model**:
1. **Stage 0 (`00-sandbox-hypervisor`)**: (Optional) Provisions an L1 "Sandbox Hypervisor VM" (`sandbox-hypervisor-node`) on the physical host with `host-passthrough` CPU virtualization (Nested KVM). Cloud-init configures `libvirtd`, AppArmor boundaries, and isolated NAT networking (`virbr0` / `192.168.122.0/24`). If a user already has an existing target hypervisor, they can bypass Stage 0.
2. **Stage 1 (`01-talos-cluster`)**: Connects remotely to the target hypervisor daemon (`qemu+ssh://ubuntu@<sandbox-ip>/system` or direct `qemu+ssh://user@<target-host>/system`) and provisions the downstream Talos Control Plane and Worker VMs inside the private cluster network.

## Consequences
- **Positive:** Complete blast-radius containment: the entire cluster can be destroyed, snapshotted, or rebuilt without modifying the physical T5600 host.
- **Positive:** Mirrors enterprise cloud VPC architecture where worker nodes reside in private subnets behind a gateway.
- **Trade-off:** Nested virtualization (L2) incurs ~5-10% CPU and memory translation overhead compared to direct bare-metal execution.
