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

## 🚀 Stand-Up Options

### Option 1: One-Command Lifecycle (`make up`)
For fast, automated stand-up of the entire platform:
```bash
# 1. Audit local workstation & target host
make doctor
make configure
make preflight

# 2. Deploy entire platform end-to-end
make up

# 3. Check cluster status & run tests
make status
make test-all

# 4. Destroy cluster when finished
make down
```

---

### Option 2: Step-by-Step Staged Stand-Up (Learning / Debugging)

---

### Step 2: Provision Virtual Infrastructure (Stages 0 & 1)
```bash
# Provision Stage 0: Nested Sandbox Hypervisor (L1 VM) - Optional if target hypervisor exists
make stage0-init
make stage0-apply
make verify-stage0

# Provision Stage 1: Downstream Talos Nodes (L2 VMs)
make stage1-init
make stage1-apply
make verify-stage1
```

---

### Step 3: Bootstrap Talos OS & Kubernetes Control Plane (Stage 2)
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
make verify-stage2
```

---

### Step 4: Deploy Platform Services (Cilium CNI & Longhorn CSI) (Stage 3)
```bash
# 1. Deploy Cilium eBPF CNI with L2 Announcement policy & Hubble
make cilium-install

# 2. Deploy Longhorn distributed block storage
make longhorn-install

# 3. Verify networking and storage readiness
make verify-stage3
```

---

### Step 5: Deploy Communicating Workloads (Stage 4) & Observability (Stage 5)
```bash
# 1. Deploy communicating microservices (frontend <-> order-api <-> redis <-> postgres)
make workload-install
make verify-stage4

# 2. Deploy Prometheus Operator, Alertmanager & Grafana Dashboards
make monitoring-install
make verify-stage5
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
