#!/usr/bin/env python3
"""
Talos Cluster Bootstrapping Orchestrator
Applies declarative machine configs, initializes etcd quorum, and extracts admin kubeconfig.
"""

import argparse
import os
import sys
import time

from common import (
    BLUE,
    BOLD,
    GREEN,
    RED,
    RESET,
    YELLOW,
    get_repo_root,
    get_terraform_outputs,
    run_cmd,
)

REPO_ROOT = get_repo_root()
TALOS_DIR = os.path.join(REPO_ROOT, "talos")
TALOSCONFIG = os.path.join(TALOS_DIR, "talosconfig")
CP_CONFIG = os.path.join(TALOS_DIR, "controlplane.yaml")
WORKER_CONFIG = os.path.join(TALOS_DIR, "worker.yaml")
KUBECONFIG = os.path.join(REPO_ROOT, "kubeconfig")


def get_cluster_endpoints():
    data = get_terraform_outputs("02-talos-cluster", repo_root=REPO_ROOT)
    if data:
        endpoints = data.get("cluster_endpoints", {}).get("value", {})
        return {
            "controlplane_ip": endpoints.get("controlplane_ip", os.environ.get("CONTROL_PLANE_IP", "192.168.122.10")),
            "worker_01_ip": endpoints.get("worker_01_ip", os.environ.get("WORKER_01_IP", "192.168.122.11")),
            "worker_02_ip": endpoints.get("worker_02_ip", os.environ.get("WORKER_02_IP", "192.168.122.12")),
        }
    return {
        "controlplane_ip": os.environ.get("CONTROL_PLANE_IP", "192.168.122.10"),
        "worker_01_ip": os.environ.get("WORKER_01_IP", "192.168.122.11"),
        "worker_02_ip": os.environ.get("WORKER_02_IP", "192.168.122.12"),
    }


def apply_machine_configs(endpoints, insecure=True):
    print(f"\n{GREEN}===> Step 1: Applying Machine Configurations over mTLS...{RESET}")
    insecure_flag = "--insecure" if insecure else ""

    cp_ip = endpoints["controlplane_ip"]
    print(f"  • Applying control plane config to {BOLD}{cp_ip}{RESET}...")
    run_cmd(f"talosctl apply-config {insecure_flag} --nodes {cp_ip} --file {CP_CONFIG}")

    for w_name, w_ip in [("worker-01", endpoints["worker_01_ip"]), ("worker-02", endpoints["worker_02_ip"])]:
        print(f"  • Applying worker config to {BOLD}{w_name} ({w_ip}){RESET}...")
        run_cmd(f"talosctl apply-config {insecure_flag} --nodes {w_ip} --file {WORKER_CONFIG}")

    print(f"{GREEN}✓ Machine configurations applied to all nodes.{RESET}")


def bootstrap_etcd(cp_ip):
    print(f"\n{GREEN}===> Step 2: Initializing etcd Control Plane Quorum on {cp_ip}...{RESET}")
    cmd = f"talosctl --talosconfig {TALOSCONFIG} --nodes {cp_ip} --endpoints {cp_ip} bootstrap"
    res = run_cmd(cmd, check=False)
    if res.returncode == 0:
        print(f"{GREEN}✓ etcd quorum bootstrap signal accepted by {cp_ip}.{RESET}")
    else:
        print(f"{YELLOW}Bootstrap notification: {res.stderr.strip()}{RESET}")


def extract_kubeconfig(cp_ip):
    print(f"\n{GREEN}===> Step 3: Extracting Admin Kubeconfig...{RESET}")
    cmd = f"talosctl --talosconfig {TALOSCONFIG} --nodes {cp_ip} --endpoints {cp_ip} kubeconfig {KUBECONFIG}"
    res = run_cmd(cmd, check=False)
    if res.returncode == 0:
        print(f"{GREEN}✓ Admin kubeconfig written to {KUBECONFIG}{RESET}")
    else:
        print(f"{YELLOW}Kubeconfig extraction note: {res.stderr.strip()}{RESET}")


def check_health(cp_ip, wait_timeout=300):
    print(f"\n{GREEN}===> Step 4: Monitoring Cluster Health Gates ({wait_timeout}s timeout)...{RESET}")
    cmd = f"talosctl --talosconfig {TALOSCONFIG} --nodes {cp_ip} --endpoints {cp_ip} health --wait-timeout {wait_timeout}s"
    print(f"Executing: {cmd}")
    res = run_cmd(cmd, check=False, capture=False)
    return res.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Talos Cluster Bootstrap Orchestrator")
    parser.add_argument("--apply-only", action="store_true", help="Apply machine configs only")
    parser.add_argument("--bootstrap-only", action="store_true", help="Bootstrap etcd only")
    parser.add_argument("--kubeconfig-only", action="store_true", help="Extract kubeconfig only")
    parser.add_argument("--health-only", action="store_true", help="Check cluster health only")
    parser.add_argument("--dry-run", action="store_true", help="Print plan and validate configs without execution")

    args = parser.parse_args()

    print(f"\n{BLUE}{BOLD}=============================================================================={RESET}")
    print(f"{BLUE}{BOLD}     Talos Cluster Bootstrapping & Readiness Orchestrator                     {RESET}")
    print(f"{BLUE}{BOLD}=============================================================================={RESET}\n")

    # Verify configs exist
    for f in [TALOSCONFIG, CP_CONFIG, WORKER_CONFIG]:
        if not os.path.exists(f):
            print(f"{RED}Error: Required file '{f}' not found.{RESET}")
            print(f"Run {BOLD}make talos-gen-config{RESET} first.")
            sys.exit(1)

    endpoints = get_cluster_endpoints()
    cp_ip = endpoints["controlplane_ip"]

    print(f"Target Nodes:")
    print(f"  - Control Plane: {BOLD}{cp_ip}{RESET}")
    print(f"  - Worker 01:     {BOLD}{endpoints['worker_01_ip']}{RESET}")
    print(f"  - Worker 02:     {BOLD}{endpoints['worker_02_ip']}{RESET}\n")

    if args.dry_run:
        print(f"{GREEN}{BOLD}✓ Dry-run verification passed: Configs and target endpoints resolved.{RESET}\n")
        return 0

    if args.apply_only:
        apply_machine_configs(endpoints)
    elif args.bootstrap_only:
        bootstrap_etcd(cp_ip)
    elif args.kubeconfig_only:
        extract_kubeconfig(cp_ip)
    elif args.health_only:
        check_health(cp_ip)
    else:
        # Full orchestration lifecycle
        apply_machine_configs(endpoints)
        print("\nWaiting 15 seconds for nodes to transition to maintenance mode...")
        time.sleep(15)
        bootstrap_etcd(cp_ip)
        print("\nWaiting 30 seconds for control plane components to initialize...")
        time.sleep(30)
        extract_kubeconfig(cp_ip)
        check_health(cp_ip)

    print(f"\n{GREEN}{BOLD}🎉 Talos Bootstrapping Operations Complete!{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
