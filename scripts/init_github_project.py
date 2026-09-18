#!/usr/bin/env python3
"""
Populates GitHub Milestones and Issues for the Talos Kubernetes Platform repository.
"""

import subprocess
import sys
import json

LABELS = [
    {"name": "area:infra", "description": "Infrastructure, KVM, & Libvirt", "color": "0E8A16"},
    {"name": "area:talos", "description": "Talos OS & Machine Configs", "color": "1D76DB"},
    {"name": "area:networking", "description": "Cilium CNI & Hubble eBPF", "color": "5319E7"},
    {"name": "area:storage", "description": "Longhorn CSI Distributed Storage", "color": "D93F0B"},
    {"name": "area:observability", "description": "Prometheus, Grafana & Metrics", "color": "E99695"},
    {"name": "area:compute", "description": "Compute, Pod Scheduling & Resources", "color": "006B75"},
    {"name": "area:gitops", "description": "ArgoCD & Continuous Delivery", "color": "0052CC"},
    {"name": "type:feature", "description": "New platform feature", "color": "A2EEEF"},
    {"name": "type:task", "description": "Implementation task", "color": "BFD4F2"},
    {"name": "type:drill", "description": "Operational or failure injection drill", "color": "FBCA04"},
]

MILESTONES = [
    {
        "title": "M1: Foundation & Virtualization (Stages 1 & 2)",
        "description": "Establish nested KVM sandbox hypervisor and downstream Talos VM infrastructure."
    },
    {
        "title": "M2: Talos OS & Control Plane Bootstrapping",
        "description": "Declarative machine configs, etcd bootstrapping, and cluster readiness validation."
    },
    {
        "title": "M3: Networking & Storage Platform",
        "description": "Deploy Cilium eBPF CNI, L2 IP Announcement, Hubble observability, and Longhorn CSI."
    },
    {
        "title": "M4: GitOps & Workload Delivery",
        "description": "ArgoCD root App-of-Apps, External Secrets Operator, and communicating training microservices."
    },
    {
        "title": "M5: Troubleshooting Drills & Diagnostic Lab",
        "description": "Drill manager CLI, automated fault injection across Compute/Network/Storage/RBAC, and 4-phase diagnostic runbooks."
    },
    {
        "title": "M6: Observability Platform (Prometheus & Grafana)",
        "description": "Deploy kube-prometheus-stack, Alertmanager, and Grafana dashboards for compute, eBPF, and CSI metrics."
    }
]

ISSUES = [
    # M1
    {
        "title": "feat(infra): Stage 1 Nested Sandbox VM module with KVM passthrough",
        "milestone": "M1: Foundation & Virtualization (Stages 1 & 2)",
        "labels": ["area:infra", "type:feature"],
        "body": "### Scope\n- Provision L1 `sandbox-hypervisor-node` VM on T5600 host.\n- Configure `host-passthrough` CPU mode for nested KVM.\n- Configure cloud-init to install libvirtd, AppArmor confinement, and isolated NAT bridge (`virbr0`).\n\n### Acceptance Criteria\n- [ ] `make stage1-init && make stage1-apply` completes with 0 errors.\n- [ ] `/dev/kvm` accessible inside sandbox VM."
    },
    {
        "title": "feat(infra): Stage 2 Downstream Talos Control Plane & Worker VM definitions",
        "milestone": "M1: Foundation & Virtualization (Stages 1 & 2)",
        "labels": ["area:infra", "type:feature"],
        "body": "### Scope\n- Connect to Stage 1 libvirt daemon.\n- Provision `talos-cp-01` (2 vCPU, 2GB RAM, 20GB OS).\n- Provision `talos-worker-01` and `talos-worker-02` (2 vCPU, 3GB RAM, 20GB OS + 30GB secondary Longhorn disk).\n\n### Acceptance Criteria\n- [ ] All 3 Talos VMs acquire DHCP leases on sandbox NAT network.\n- [ ] Secondary disk `/dev/vdb` attached to worker nodes."
    },
    {
        "title": "test(infra): Automated hypervisor & network verification checks",
        "milestone": "M1: Foundation & Virtualization (Stages 1 & 2)",
        "labels": ["area:infra", "type:task"],
        "body": "### Scope\n- Automated Python verification script testing SSH connectivity, libvirt socket, and domain states.\n\n### Acceptance Criteria\n- [ ] `make verify-stage1` and `make verify-stage2` pass."
    },

    # M2
    {
        "title": "feat(talos): Generate declarative machine configs with Cilium & storage patches",
        "milestone": "M2: Talos OS & Control Plane Bootstrapping",
        "labels": ["area:talos", "type:feature"],
        "body": "### Scope\n- Generate Talos cluster configuration (`controlplane.yaml`, `worker.yaml`).\n- Apply machine config patches to disable standard `kube-proxy` and flannel (for Cilium).\n\n### Acceptance Criteria\n- [ ] Config files generated cleanly in `talos/`.\n- [ ] No unencrypted private keys committed to Git."
    },
    {
        "title": "feat(talos): Bootstrap etcd quorum and control plane health gates",
        "milestone": "M2: Talos OS & Control Plane Bootstrapping",
        "labels": ["area:talos", "type:feature"],
        "body": "### Scope\n- Apply machine configs over mTLS via `talosctl apply-config`.\n- Bootstrap etcd via `talosctl bootstrap`.\n\n### Acceptance Criteria\n- [ ] `talosctl health` confirms etcd quorum and API server health."
    },
    {
        "title": "feat(talos): Extract admin kubeconfig & verify node readiness",
        "milestone": "M2: Talos OS & Control Plane Bootstrapping",
        "labels": ["area:talos", "type:feature"],
        "body": "### Scope\n- Extract admin kubeconfig via `talosctl kubeconfig`.\n- Verify node registration in Kubernetes API.\n\n### Acceptance Criteria\n- [ ] `kubectl get nodes -o wide` displays all 3 nodes registered."
    },

    # M3
    {
        "title": "feat(cni): Deploy Cilium in eBPF kube-proxy replacement mode",
        "milestone": "M3: Networking & Storage Platform",
        "labels": ["area:networking", "type:feature"],
        "body": "### Scope\n- Deploy Cilium CNI Helm chart.\n- Configure eBPF kube-proxy replacement.\n\n### Acceptance Criteria\n- [ ] `cilium status` reports healthy eBPF datapath across all nodes."
    },
    {
        "title": "feat(cni): Configure Cilium L2 IP Announcement & Hubble UI",
        "milestone": "M3: Networking & Storage Platform",
        "labels": ["area:networking", "type:feature"],
        "body": "### Scope\n- Configure Cilium L2 Announcement Policy for LoadBalancer services.\n- Enable Hubble flow exporter and Hubble UI.\n\n### Acceptance Criteria\n- [ ] LoadBalancer services assign IP without MetalLB.\n- [ ] Hubble UI reachable and streaming live network flows."
    },
    {
        "title": "feat(storage): Deploy Longhorn CSI & verify dynamic multi-node PVC replication",
        "milestone": "M3: Networking & Storage Platform",
        "labels": ["area:storage", "type:feature"],
        "body": "### Scope\n- Deploy Longhorn CSI utilizing `/dev/vdb` storage disks.\n- Verify default StorageClass.\n\n### Acceptance Criteria\n- [ ] Dynamic PVC provisioning tested with synchronous 2-replica redundancy."
    },

    # M4
    {
        "title": "feat(gitops): Deploy ArgoCD and Root App-of-Apps controller",
        "milestone": "M4: GitOps & Workload Delivery",
        "labels": ["area:gitops", "type:feature"],
        "body": "### Scope\n- Deploy ArgoCD in `argocd` namespace.\n- Configure root `Application` manifest tracking `gitops/` directory.\n\n### Acceptance Criteria\n- [ ] ArgoCD synchronizes all platform add-ons automatically."
    },
    {
        "title": "feat(secrets): Integrate External Secrets Operator",
        "milestone": "M4: GitOps & Workload Delivery",
        "labels": ["area:gitops", "type:feature"],
        "body": "### Scope\n- Deploy External Secrets Operator (ESO).\n- Configure SecretStore provider for secure secret distribution.\n\n### Acceptance Criteria\n- [ ] K8s secrets synchronized dynamically without committing plaintext secrets to Git."
    },
    {
        "title": "feat(apps): Deploy CloudNativePG HA Postgres cluster with anti-affinity",
        "milestone": "M4: GitOps & Workload Delivery",
        "labels": ["area:gitops", "type:feature"],
        "body": "### Scope\n- Deploy CloudNativePG operator.\n- Create a 2-instance PostgreSQL cluster with pod anti-affinity.\n\n### Acceptance Criteria\n- [ ] Primary and replica pods scheduled on separate worker VMs."
    },
    {
        "title": "feat(apps): Deploy multi-tier communicating microservices training application",
        "milestone": "M4: GitOps & Workload Delivery",
        "labels": ["area:gitops", "type:feature"],
        "body": "### Scope\n- Deploy multi-tier communicating application in `training` namespace.\n- Configure frontend, order-api, redis-cache, postgres-db, and queue-worker.\n\n### Acceptance Criteria\n- [ ] `make workload-install` deploys all microservice components."
    },

    # M5
    {
        "title": "feat(drills): Implement Drill Manager CLI for automated failure injection and healing",
        "milestone": "M5: Troubleshooting Drills & Diagnostic Lab",
        "labels": ["type:drill", "area:compute", "area:networking", "area:storage"],
        "body": "### Scope\n- Develop `scripts/drill_manager.py` CLI supporting `--list`, `--inject`, `--verify`, and `--heal`.\n\n### Acceptance Criteria\n- [ ] `make drill-list` displays all scenarios."
    },
    {
        "title": "docs(drills): Author guided 4-phase troubleshooting runbooks for cluster failure scenarios",
        "milestone": "M5: Troubleshooting Drills & Diagnostic Lab",
        "labels": ["documentation", "type:drill"],
        "body": "### Scope\n- Establish standardized 4-Phase Diagnostic Framework (Detect -> Isolate -> Root Cause -> Remediate).\n\n### Acceptance Criteria\n- [ ] Runbooks for compute, networking, and storage in `docs/troubleshooting-drills/`."
    },
    {
        "title": "test(drills): Execute node drain, rolling reboot, and failover validation",
        "milestone": "M5: Troubleshooting Drills & Diagnostic Lab",
        "labels": ["type:drill"],
        "body": "### Scope\n- Execute `kubectl cordon` & `kubectl drain` on `talos-worker-01`.\n- Validate database failover and zero-downtime workload migration.\n\n### Acceptance Criteria\n- [ ] Document drill results in `docs/03-disaster-recovery-drills.md`."
    },
    {
        "title": "test(drills): Perform volume snapshot corruption and restore drill",
        "milestone": "M5: Troubleshooting Drills & Diagnostic Lab",
        "labels": ["type:drill", "area:storage"],
        "body": "### Scope\n- Take Longhorn VolumeSnapshot of Postgres database.\n- Simulate data corruption and restore volume from snapshot.\n\n### Acceptance Criteria\n- [ ] Data verified intact after snapshot restoration."
    },

    # M6
    {
        "title": "feat(observability): Deploy Prometheus Operator and kube-prometheus-stack",
        "milestone": "M6: Observability Platform (Prometheus & Grafana)",
        "labels": ["area:observability", "type:feature"],
        "body": "### Scope\n- Configure and deploy `kube-prometheus-stack` via Helm in `monitoring` namespace.\n\n### Acceptance Criteria\n- [ ] `make monitoring-install` deploys without errors."
    },
    {
        "title": "feat(observability): Preconfigure Grafana dashboards for Compute, eBPF CNI, and CSI Storage",
        "milestone": "M6: Observability Platform (Prometheus & Grafana)",
        "labels": ["area:observability", "type:feature"],
        "body": "### Scope\n- Curate Grafana dashboards for Compute, Cilium eBPF packet drops, and Longhorn dynamic PVC metrics.\n\n### Acceptance Criteria\n- [ ] Dashboards load metrics automatically upon Grafana login."
    }
]

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error running: {cmd}\n{res.stderr}")
    return res

def main():
    print("Ensuring Labels...")
    for label in LABELS:
        cmd = f"gh label create \"{label['name']}\" --description \"{label['description']}\" --color \"{label['color']}\" --force"
        run_cmd(cmd)

    print("\nCreating / Verifying Milestones...")
    milestone_map = {}
    for m in MILESTONES:
        cmd = f"gh api repos/:owner/:repo/milestones -f title=\"{m['title']}\" -f description=\"{m['description']}\""
        res = run_cmd(cmd)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            milestone_map[m["title"]] = data.get("number")
            print(f"  ✓ Milestone synced: {m['title']} (#{data.get('number')})")

    # If milestones already exist, fetch them
    if not milestone_map:
        res = run_cmd("gh api repos/:owner/:repo/milestones")
        if res.returncode == 0:
            for item in json.loads(res.stdout):
                milestone_map[item["title"]] = item["number"]

    print("\nCreating Issues...")
    for issue in ISSUES:
        m_num = milestone_map.get(issue["milestone"])
        labels_arg = ",".join(issue["labels"])
        m_arg = f"--milestone \"{issue['milestone']}\"" if m_num else ""
        
        cmd = f"gh issue create --title \"{issue['title']}\" --body \"{issue['body']}\" --label \"{labels_arg}\" {m_arg}"
        res = run_cmd(cmd)
        if res.returncode == 0:
            print(f"  ✓ Issue synced: {issue['title']}")

    print("\n🎉 GitHub Project Management synchronization complete!")

if __name__ == "__main__":
    main()

