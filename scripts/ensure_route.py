#!/usr/bin/env python3
"""
Talos Kubernetes Platform - Dynamic Cluster Subnet Route Manager
Detects the cluster subnet from Terraform/kubeconfig/libvirt and ensures
the local workstation has an active route via the target hypervisor host.
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
    YELLOW,
    get_cluster_cidr,
    get_target_host,
)


def check_conflicting_interface(cidr: str) -> bool:
    """Check if a local interface (e.g. virbr0) conflicts with the discovered subnet."""
    try:
        res = subprocess.run(["ip", "-o", "addr", "show"], capture_output=True, text=True)
        if res.returncode == 0:
            prefix = cidr.rsplit(".", 1)[0]  # e.g., '192.168.122'
            for line in res.stdout.splitlines():
                if prefix in line and not line.strip().startswith("lo"):
                    parts = line.split()
                    if len(parts) >= 2:
                        iface = parts[1]
                        if iface.startswith("virbr") or iface.startswith("br-"):
                            print(f"{YELLOW}Warning: Local interface '{iface}' is using subnet prefix '{prefix}'.{RESET}")
                            print(f"{YELLOW}If traffic does not reach the remote cluster, you may need to down or re-address '{iface}'.{RESET}")
                            return True
    except Exception:
        pass
    return False


def is_route_active(cidr: str, target_host: str) -> bool:
    """Check if the route to the target CIDR is already present via target_host."""
    try:
        res = subprocess.run(["ip", "route", "show", cidr], capture_output=True, text=True)
        route_out = res.stdout.strip()
        if target_host in route_out or ("via" in route_out and target_host in route_out):
            return True
    except Exception:
        pass
    return False


def ensure_route(cidr: str, target_host: str) -> bool:
    """Ensure the route exists, creating or updating it with sudo if necessary."""
    if is_route_active(cidr, target_host):
        return True

    print(f"{BLUE}===> Configuring workstation route for cluster subnet {BOLD}{cidr}{RESET} {BLUE}via {BOLD}{target_host}{RESET}...")
    check_conflicting_interface(cidr)

    cmd = ["sudo", "ip", "route", "replace", cidr, "via", target_host]
    try:
        res = subprocess.run(cmd)
        if res.returncode == 0:
            print(f"{GREEN}✓ Route configured: {cidr} via {target_host}{RESET}")
            return True
        else:
            print(f"{RED}✗ Failed to add route (exit code {res.returncode}).{RESET}")
            return False
    except Exception as e:
        print(f"{RED}✗ Error executing sudo ip route: {e}{RESET}")
        return False


def delete_route(cidr: str, target_host: str) -> bool:
    """Remove the route from the local routing table."""
    cmd = ["sudo", "ip", "route", "del", cidr, "via", target_host]
    try:
        res = subprocess.run(cmd)
        return res.returncode == 0
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Talos Cluster Dynamic Subnet Route Manager")
    parser.add_argument("--check", action="store_true", help="Check if route is active without modifying system table")
    parser.add_argument("--print-cidr", action="store_true", help="Print discovered cluster CIDR and exit")
    parser.add_argument("--delete", action="store_true", help="Delete the route from the routing table")
    parser.add_argument("--quiet", action="store_true", help="Suppress non-error output")

    args = parser.parse_args()

    target_host = get_target_host()
    if not target_host or target_host in ("127.0.0.1", "localhost"):
        if not args.quiet:
            print(f"{GREEN}Target host is local ({target_host or 'localhost'}). No routing required.{RESET}")
        return 0

    cidr = get_cluster_cidr()
    if not cidr:
        print(f"{RED}Error: Could not dynamically determine cluster subnet CIDR from Terraform, kubeconfig, or target host.{RESET}")
        print(f"Tip: You can declare TARGET_CLUSTER_CIDR=192.168.122.0/24 in target.env")
        return 1

    if args.print_cidr:
        print(cidr)
        return 0

    if args.delete:
        if delete_route(cidr, target_host):
            print(f"{GREEN}✓ Route removed: {cidr} via {target_host}{RESET}")
            return 0
        else:
            print(f"{RED}✗ Failed to remove route.{RESET}")
            return 1

    if args.check:
        if is_route_active(cidr, target_host):
            if not args.quiet:
                print(f"{GREEN}✓ Route is active: {cidr} via {target_host}{RESET}")
            return 0
        else:
            if not args.quiet:
                print(f"{YELLOW}Route missing: {cidr} via {target_host}{RESET}")
            return 1

    # Default: ensure route is present
    success = ensure_route(cidr, target_host)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
