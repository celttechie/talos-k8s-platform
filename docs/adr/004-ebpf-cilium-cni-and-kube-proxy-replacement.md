# ADR 004: eBPF Cilium CNI and Kube-Proxy Replacement

## Status
Accepted

## Context
Standard Kubernetes networking relies on legacy `iptables` or `ipvs` via `kube-proxy` for service routing and packet filtering. At scale, large `iptables` rule chains cause sequential packet traversal latency, lack Layer 7 observability, and require separate tooling (e.g. MetalLB) for bare-metal/homelab LoadBalancer services.

## Decision
We deploy **Cilium CNI** in full **eBPF Kube-Proxy Replacement Mode**:
1. **Kernel-Level eBPF Datapath**: Replace `kube-proxy` entirely by attaching eBPF programs directly to Linux socket and XDP/TC hooks, achieving $O(1)$ hash-map service lookups.
2. **Layer 2 IP Announcement**: Enable Cilium L2 Announcements (via ARP responder) to natively assign `LoadBalancer` IPs from a dedicated homelab pool without installing MetalLB.
3. **Hubble Observability**: Enable Cilium Hubble daemon and UI for real-time L3/L4/L7 flow auditing, DNS resolution tracking, and network policy visual validation.

## Consequences
- **Positive:** Maximum networking throughput and microsecond-level service routing latency.
- **Positive:** Deep observability into inter-service communications and dropped packets via Hubble.
- **Positive:** Unifies CNI, Ingress/Gateway API, NetworkPolicy enforcement, and LoadBalancer VIP management into a single control plane.
- **Trade-off:** Requires kernel eBPF support and specific Talos machine configuration patches to disable standard `kube-proxy` and flannel.
