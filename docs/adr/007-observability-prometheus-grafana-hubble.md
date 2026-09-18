# ADR 007: Prometheus Operator, Grafana, and Hubble for Cluster Observability

## Status
Accepted

## Context
Diagnosing complex distributed failures across compute, eBPF networking, and distributed block storage requires comprehensive, correlated metrics and packet flow visibility. A unified observability stack is necessary to provide both historical telemetry and real-time network flow inspection.

## Decision
We deploy **kube-prometheus-stack** along with **Cilium Hubble UI**:
1. **Prometheus Operator**: Manages Prometheus and Alertmanager instances with declarative `ServiceMonitor` and `PrometheusRule` resources.
2. **Curated Grafana Dashboards**: Provides purpose-built visual dashboards for Workload/Compute Pressure, Cilium eBPF Packet Drops, Longhorn CSI Latency, and Application Golden Signals.
3. **Hubble UI & Flow Relay**: Provides socket-level visibility into container networking flows, DNS resolution, and security policy drops.

## Consequences
- **Positive:** Immediate, visual feedback during troubleshooting drills and cluster operations.
- **Positive:** Standardized alerting rules for memory leaks, CPU quota saturation, and degraded storage replicas.
- **Trade-off:** Observability components consume dedicated memory and CPU resources on worker nodes (~1-1.5GB total).
