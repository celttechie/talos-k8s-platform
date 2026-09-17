#!/usr/bin/env python3
"""
Populates GitHub Milestones and Issues for the Talos Kubernetes Platform repository.
"""

import subprocess
import sys
import json

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
        "description": "ArgoCD root App-of-Apps, External Secrets Operator, and CloudNativePG HA Postgres cluster."
    },
    {
        "title": "M5: Operational Drills & Failure Testing",
        "description": "Node drain, rolling reboots, volume snapshot recovery drills, and disaster recovery runbooks."
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

    # M5
    {
        "title": "test(drills): Execute node drain, rolling reboot, and failover validation",
        "milestone": "M5: Operational Drills & Failure Testing",
        "labels": ["type:drill"],
        "body": "### Scope\n- Execute `kubectl cordon` & `kubectl drain` on `talos-worker-01`.\n- Validate database failover and zero-downtime workload migration.\n\n### Acceptance Criteria\n- [ ] Document drill results in `docs/03-disaster-recovery-drills.md`."
    },
    {
        "title": "test(drills): Perform volume snapshot corruption and restore drill",
        "milestone": "M5: Operational Drills & Failure Testing",
        "labels": ["type:drill", "area:storage"],
        "body": "### Scope\n- Take Longhorn VolumeSnapshot of Postgres database.\n- Simulate data corruption and restore volume from snapshot.\n\n### Acceptance Criteria\n- [ ] Data verified intact after snapshot restoration."
    }
]

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error running: {cmd}\n{res.stderr}")
    return res

def main():
    print("Creating Milestones...")
    milestone_map = {}
    for m in MILESTONES:
        cmd = f"gh api repos/:owner/:repo/milestones -f title=\"{m['title']}\" -f description=\"{m['description']}\""
        res = run_cmd(cmd)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            milestone_map[m["title"]] = data.get("number")
            print(f"  ✓ Milestone created: {m['title']} (#{data.get('number')})")

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
            print(f"  ✓ Issue created: {issue['title']}")

    print("\n🎉 GitHub Project Management initialization complete!")

if __name__ == "__main__":
    main()
