# Cluster Bootstrap, Verification & Learning Guide

This guide provides the complete, step-by-step procedure to stand up the **Talos Kubernetes Platform** from bare metal to a fully observable, operational training laboratory.

---

## 📋 Prerequisites Checklist

Ensure your developer workstation has the required tools installed (`make doctor`):
- **Terraform** $\ge$ 1.5.0
- **talosctl** $\ge$ 1.8.0
- **kubectl** $\ge$ 1.30.0
- **helm** $\ge$ 3.14.0
- **Python** $\ge$ 3.10

---

## 🚀 Step-by-Step Stand-Up Procedure

### Step 1: Workstation & Server Configuration
```bash
# 1. Audit local workstation toolchain
make doctor

# 2. Configure target deployment server (Dell T5600)
make configure

# 3. Validate target hypervisor (KVM, libvirtd, storage pools, network bridges)
make preflight
```

---

### Step 2: Provision Virtual Infrastructure (Stages 1 & 2)
```bash
# Provision Stage 1: Nested Sandbox Hypervisor (L1 VM)
make stage1-init
make stage1-apply
make verify-stage1

# Provision Stage 2: Downstream Talos Nodes (L2 VMs)
make stage2-init
make stage2-apply
make verify-stage2
```

---

### Step 3: Bootstrap Talos OS & Kubernetes Control Plane
```bash
# 1. Generate declarative machine configs with Cilium & Longhorn patches
make talos-gen-config

# 2. Apply machine configs to Control Plane & Worker nodes
make talos-apply-config

# 3. Initialize etcd control plane quorum
make talos-bootstrap

# 4. Extract admin kubeconfig
make talos-kubeconfig

# 5. Audit control plane health
make talos-health
make verify-stage3
```

---

### Step 4: Deploy Platform Services (Cilium CNI & Longhorn CSI)
```bash
# 1. Deploy Cilium eBPF CNI with L2 Announcement policy & Hubble
make cilium-install

# 2. Deploy Longhorn distributed block storage
make longhorn-install

# 3. Verify networking and storage readiness
make verify-stage4
```

---

### Step 5: Deploy Communicating Workloads & Observability
```bash
# 1. Deploy communicating microservices (frontend <-> order-api <-> redis <-> postgres)
make workload-install

# 2. Deploy Prometheus Operator, Alertmanager & Grafana Dashboards
make monitoring-install

# 3. Verify GitOps and observability stack
make verify-stage5
make verify-stage6
```

---

## 📊 Accessing Observability & Visual Dashboards

| Tool | Access Command | Local URL | Credentials |
| :--- | :--- | :--- | :--- |
| **Grafana** | `make grafana` | `http://localhost:3000` | `admin` / `prom-operator` |
| **Hubble UI** | `make hubble-ui` | `http://localhost:12000` | No auth (local) |
| **Longhorn UI** | `kubectl port-forward -n longhorn-system svc/longhorn-frontend 8080:80` | `http://localhost:8080` | No auth (local) |

---

## 🧪 Hands-On Troubleshooting & Learning Protocol

Once the cluster is running, use the **4-Phase Diagnostic Framework** ([`docs/troubleshooting-drills/`](troubleshooting-drills/README.md)) to practice finding and fixing common cluster issues:

```bash
# 1. List all available drill scenarios
make drill-list

# 2. Inject a failure scenario (e.g. OOM killed, packet drop, port mismatch, pending PVC)
make drill-inject SCENARIO=comp-oom-killed

# 3. Follow the diagnostic runbook to isolate and identify the root cause
# Inspect with:
make drill-verify SCENARIO=comp-oom-killed
# Or inspect live metrics in Grafana (http://localhost:3000) and Hubble UI (http://localhost:12000)

# 4. Restore the cluster to a healthy state
make drill-heal SCENARIO=comp-oom-killed
```

### Domain Diagnostic Runbooks:
- [Domain 1: Compute & Scheduling Runbooks](troubleshooting-drills/01-compute-drills.md) (OOMKilled, CPU Throttling, Unschedulable Pods, Probe Failures)
- [Domain 2: Networking & eBPF Runbooks](troubleshooting-drills/02-networking-drills.md) (DNS Outages, CiliumNetworkPolicy Drops, TargetPort & Selector Mismatches)
- [Domain 3: Storage & CSI Runbooks](troubleshooting-drills/03-storage-drills.md) (Unsatisfied PVCs, Multi-Attach Errors, Longhorn Replica Degradation)
- [Disaster Recovery & Node Drain Drills](03-disaster-recovery-drills.md) (Live node eviction, zero-downtime failover, CSI VolumeSnapshot restoration)
