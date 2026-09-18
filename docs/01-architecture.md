# Platform Architecture & Design Guide

This document describes the technical architecture, nested virtualization topology, network routing, distributed storage mechanics, and telemetry pipeline of the **Talos Kubernetes Platform & Troubleshooting Laboratory**.

---

## 1. Physical & Nested Virtualization Topology

The platform operates on a Dell Precision T5600 bare-metal server using KVM hardware virtualization:

```mermaid
flowchart TD
    subgraph Host ["Physical Hypervisor: Dell Precision T5600"]
        BareMetal["Ubuntu Linux Server (Libvirtd + KVM)\nHost IP: target.env (TARGET_HOST)"]
        
        subgraph Stage1 ["Stage 1: Nested Sandbox Hypervisor (L1 VM)"]
            SandboxVM["sandbox-hypervisor-node (Ubuntu 24.04 LTS)\nNested KVM Passthrough (/dev/kvm)\n8 vCPU | 12GB RAM | 60GB Disk\nNAT Bridge: virbr0 (192.168.122.0/24)"]
            
            subgraph Stage2 ["Stage 2: Talos Kubernetes Cluster (L2 VMs)"]
                CP["talos-cp-01 (Control Plane)\n2 vCPU | 2GB RAM | 20GB OS (/dev/vda)\nIP: 192.168.122.10"]
                W1["talos-worker-01 (Worker 1)\n2 vCPU | 3GB RAM\n20GB OS (/dev/vda) + 30GB Storage (/dev/vdb)\nIP: 192.168.122.11"]
                W2["talos-worker-02 (Worker 2)\n2 vCPU | 3GB RAM\n20GB OS (/dev/vda) + 30GB Storage (/dev/vdb)\nIP: 192.168.122.12"]
            end
        end
    end

    BareMetal --> SandboxVM
    SandboxVM --> CP
    SandboxVM --> W1
    SandboxVM --> W2
```

### Key Architectural Benefits
- **Complete Host Isolation:** All Kubernetes nodes live inside the destroyable `sandbox-hypervisor-node` VM, preventing pollution of the physical hypervisor.
- **Zero SSH / Immutable OS:** Talos Linux eliminates shell access, package managers, and systemd in favor of declarative YAML configuration managed over an mTLS API on port `50000`.

---

## 2. eBPF Networking & Service Routing (Cilium CNI)

Cilium replaces standard `kube-proxy` and iptables with high-performance eBPF datapaths:

```mermaid
flowchart LR
    Client["In-Cluster Pod / Client"] -->|TCP SYN| eBPF["Cilium eBPF Datapath\n(kubeProxyReplacement: true)"]
    eBPF -->|Socket-Level Translation| Backend["Target Service Endpoint (Pod)"]
    eBPF -.->|Flow Telemetry| Hubble["Hubble Relay & Flow Visualizer"]
    eBPF -.->|Drop Metrics| Prom["Prometheus Scrapers"]
```

### Highlights
- **Direct Server Return (DSR) & Socket Load Balancing:** Eliminates extra network hops and preserves client source IPs.
- **Layer 2 IP Announcements:** Hosts LoadBalancer virtual IPs on the local network (`192.168.122.200/29`) without needing MetalLB.
- **Hubble Flow Visibility:** Inspects every socket-level connection, packet drop, DNS lookup, and HTTP latency in real-time.

---

## 3. Dynamic Distributed Block Storage (Longhorn CSI)

Longhorn provides resilient, replicated persistent volumes across worker nodes using dedicated virtual disks:

```mermaid
flowchart TD
    App["PostgreSQL / StatefulSet"] -->|Mounts| PVC["PersistentVolumeClaim (RWO / RWX)"]
    PVC -->|Managed by| CSI["Longhorn CSI Controller"]
    CSI --> Replica1["Replica 1 (/var/lib/longhorn on W1 - /dev/vdb)"]
    CSI --> Replica2["Replica 2 (/var/lib/longhorn on W2 - /dev/vdb)"]
```

- **Replication:** Each dynamic volume is mirrored synchronously across `talos-worker-01` and `talos-worker-02`.
- **Automatic Self-Healing:** If a worker node is drained or detached, Longhorn marks the volume as `Degraded` and triggers automated rebuilding upon node reconnection.
- **VolumeSnapshots:** Integration with CSI `VolumeSnapshotClass` enables instant point-in-time backups and recovery.

---

## 4. Observability & Telemetry Pipeline

```mermaid
flowchart LR
    Nodes["Talos Kubelets & Nodes"] -->|Metrics| Prom["Prometheus Operator\n(kube-prometheus-stack)"]
    CiliumAgent["Cilium eBPF Agents"] -->|Flow & Drop Metrics| Prom
    LonghornCSI["Longhorn Storage Engine"] -->|IOPS & Health| Prom
    Workloads["Microservices Golden Signals"] -->|Rate / Errors / Latency| Prom

    Prom --> Grafana["Grafana Dashboards\n- Compute Pressure\n- eBPF Drops\n- CSI Latency"]
    Prom --> Alerts["Alertmanager\n- OOM Warning\n- CFS Throttle >60%\n- Degraded Volume"]
    CiliumAgent --> HubbleUI["Hubble Visual UI (Port 12000)"]
```
