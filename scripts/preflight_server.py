#!/usr/bin/env python3
"""
Talos Kubernetes Platform - Target Server Pre-Flight Validator
Audits the target hypervisor host for hardware virtualization,
KVM kernel modules, memory capacity, remote libvirt daemon health, storage pools, and network bridges.
"""

import argparse
import subprocess
import sys

from common import (
    BLUE,
    BOLD,
    GREEN,
    RED,
    RESET,
    get_target_host,
)

CHECKS = []

def record(name, passed, status, purpose):
    CHECKS.append((name, passed, status, purpose))


def main():
    default_host = get_target_host() or ""
    parser = argparse.ArgumentParser(description="Target Hypervisor Server Pre-Flight Diagnostics")
    parser.add_argument("--host", default=default_host, help=f"SSH hostname or IP of the target hypervisor server (default: {default_host or 'target.env'})")
    args = parser.parse_args()

    server_host = args.host
    if not server_host:
        print(f"\n{RED}{BOLD}Error: No target host specified. Run 'make configure' or pass --host <server>{RESET}\n")
        return 1

    ssh_base = ["ssh", "-o", "ConnectTimeout=3", "-o", "StrictHostKeyChecking=no", server_host]

    print(f"\n{BLUE}{BOLD}=============================================================================={RESET}")
    print(f"{BLUE}{BOLD}     Target Hypervisor Server Pre-Flight Check ({server_host})               {RESET}")
    print(f"{BLUE}{BOLD}=============================================================================={RESET}\n")

    # 1. SSH Connectivity & Host Identification
    try:
        res = subprocess.run(ssh_base + ["hostname"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            hostname = res.stdout.strip()
            record(f"SSH Reachability ({server_host})", True, f"{GREEN}OK{RESET} (Host: {hostname})", "Remote Orchestration")
        else:
            record(f"SSH Reachability ({server_host})", False, f"{RED}FAILED{RESET} ({res.stderr.strip()})", "Remote Orchestration")
            print(f"{RED}{BOLD}Cannot reach target host '{server_host}' via SSH. Check ~/.ssh/config and network connection.{RESET}\n")
            return 1
    except Exception as e:
        record(f"SSH Reachability ({server_host})", False, f"{RED}UNREACHABLE{RESET} ({e})", "Remote Orchestration")
        print(f"{RED}{BOLD}SSH connection timed out to '{server_host}'.{RESET}\n")
        return 1

    # 2. Hardware KVM Passthrough (/dev/kvm)
    res = subprocess.run(ssh_base + ["[ -e /dev/kvm ] && echo OK || echo MISSING"], capture_output=True, text=True)
    has_kvm = "OK" in res.stdout
    record("Hardware KVM (/dev/kvm)", has_kvm, f"{GREEN}OK{RESET} (/dev/kvm present)" if has_kvm else f"{RED}MISSING{RESET}", "Virtualization Engine")

    # 3. CPU Virtualization Flags
    res = subprocess.run(ssh_base + ["grep -E -c '(vmx|svm)' /proc/cpuinfo"], capture_output=True, text=True)
    cpu_cores = res.stdout.strip()
    has_vmx = cpu_cores.isdigit() and int(cpu_cores) > 0
    record("CPU Virtualization Extensions", has_vmx, f"{GREEN}OK{RESET} ({cpu_cores} VMX/SVM threads)" if has_vmx else f"{RED}DISABLED IN BIOS{RESET}", "Nested Hypervisors")

    # 4. Host Compute RAM Capacity
    res = subprocess.run(ssh_base + ["free -h | awk '/Mem:/ {print $2, \"total,\", $7, \"avail\"}'"], capture_output=True, text=True)
    mem_info = res.stdout.strip()
    record("Memory Capacity", bool(mem_info), f"{GREEN}OK{RESET} ({mem_info})", "VM Allocations")

    # 5. Remote Libvirtd Daemon Responsiveness
    res = subprocess.run(ssh_base + ["virsh -c qemu:///system list --all >/dev/null 2>&1 && echo OK || echo FAIL"], capture_output=True, text=True)
    libvirtd_ok = "OK" in res.stdout
    record("Libvirtd System Daemon", libvirtd_ok, f"{GREEN}OK{RESET} (qemu:///system responsive)" if libvirtd_ok else f"{RED}UNRESPONSIVE{RESET}", "Hypervisor Management")

    # 6. Libvirt Storage Pools
    res = subprocess.run(ssh_base + ["virsh -c qemu:///system pool-list --all"], capture_output=True, text=True)
    pools = [line.split()[0] for line in res.stdout.splitlines()[2:] if line.strip() and "active" in line]
    has_pools = bool(pools)
    pool_str = ", ".join(pools) if pools else "None active"
    record("Storage Pools", has_pools, f"{GREEN}OK{RESET} ({pool_str})" if has_pools else f"{RED}NO ACTIVE POOLS{RESET}", "VM Disk Storage")

    # 7. Virtual Network Bridges
    res = subprocess.run(ssh_base + ["virsh -c qemu:///system net-list --all"], capture_output=True, text=True)
    nets = [line.split()[0] for line in res.stdout.splitlines()[2:] if line.strip() and "active" in line]
    has_net = bool(nets)
    net_str = ", ".join(nets) if nets else "None active"
    record("Network Bridges", has_net, f"{GREEN}OK{RESET} ({net_str})" if has_net else f"{RED}NO ACTIVE BRIDGES{RESET}", "VM Networking")

    # 8. Host Kernel IP Forwarding
    res = subprocess.run(ssh_base + ["sysctl -n net.ipv4.ip_forward"], capture_output=True, text=True)
    ip_fwd = res.stdout.strip() == "1"
    record("Kernel IP Forwarding", ip_fwd, f"{GREEN}ENABLED{RESET} (net.ipv4.ip_forward=1)" if ip_fwd else f"{RED}DISABLED (Run `sysctl -w net.ipv4.ip_forward=1`){RESET}", "Routed VM Traffic")

    all_passed = True
    print(f"{BOLD}{'Server Resource / Check':<32} {'Status':<36} {'Purpose'}{RESET}")
    print("-" * 80)
    for name, ok, status, purpose in CHECKS:
        if not ok:
            all_passed = False
        print(f"{name:<32} {status:<36} {purpose}")

    print("\n" + "-" * 80)
    if all_passed:
        print(f"{GREEN}{BOLD}🎉 Target server '{server_host}' is 100% healthy and ready for VM provisioning!{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}❌ Target server has failing pre-flight checks (see above).{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
