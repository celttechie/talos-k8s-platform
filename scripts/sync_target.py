#!/usr/bin/env python3
"""
Talos Kubernetes Platform - Target Synchronizer
Automatically extracts Stage 0 Sandbox VM hypervisor details (IP, credentials, libvirt URI)
and updates target.env and 01-talos-cluster/terraform.tfvars so downstream automation
seamlessly and identically targets the sandbox VM.
"""

import argparse
import os
import sys

from common import (
    BLUE,
    BOLD,
    GREEN,
    RED,
    RESET,
    YELLOW,
    get_repo_root,
    get_terraform_outputs,
    load_target_env,
)

REPO_ROOT = get_repo_root()


def sync_sandbox_target(quiet=False):
    """Extract Stage 0 sandbox VM details and update downstream configs."""
    tf_out = get_terraform_outputs("00-sandbox-hypervisor", repo_root=REPO_ROOT)
    if not tf_out or "sandbox_ip_address" not in tf_out:
        if not quiet:
            print(f"{YELLOW}ℹ No active Stage 0 sandbox VM outputs found in terraform state.{RESET}")
        return False

    sandbox_ip = tf_out["sandbox_ip_address"].get("value")
    if not sandbox_ip or sandbox_ip in ("pending-dhcp", ""):
        if not quiet:
            print(f"{RED}✗ Stage 0 sandbox IP address is not available or pending DHCP lease.{RESET}")
        return False

    # Retrieve existing configuration preferences
    current_env = load_target_env(os.path.join(REPO_ROOT, "target.env"))
    base_host = current_env.get("TARGET_BASE_HOST") or current_env.get("TARGET_HOST", "192.168.9.110")
    ssh_key = current_env.get("TARGET_SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519"))
    if not os.path.exists(ssh_key):
        # Fallback search
        for candidate in ["~/.ssh/id_ed25519", "~/.ssh/id_rsa"]:
            expanded = os.path.expanduser(candidate)
            if os.path.exists(expanded):
                ssh_key = expanded
                break

    ssh_pubkey = current_env.get("TARGET_SSH_PUBKEY", ssh_key + ".pub" if os.path.exists(ssh_key + ".pub") else ssh_key)
    user = "ubuntu"
    pool_name = current_env.get("TARGET_STORAGE_POOL", "default")
    net_name = current_env.get("TARGET_NETWORK", "default")

    libvirt_uri = f"qemu+ssh://{user}@{sandbox_ip}/system?keyfile={ssh_key}"

    if not quiet:
        print(f"\n{BLUE}{BOLD}=============================================================================={RESET}")
        print(f"{BLUE}{BOLD}     Synchronizing Stage 0 Sandbox VM Target to Downstream Stage 1            {RESET}")
        print(f"{BLUE}{BOLD}=============================================================================={RESET}\n")
        print(f"  Base Hypervisor Host: {BOLD}{base_host}{RESET}")
        print(f"  Target Sandbox IP:    {BOLD}{sandbox_ip}{RESET}")
        print(f"  Target User:          {BOLD}{user}{RESET}")
        print(f"  Target Libvirt URI:   {BOLD}{libvirt_uri}{RESET}")

    # 1. Update target.env
    target_env_path = os.path.join(REPO_ROOT, "target.env")
    with open(target_env_path, "w") as f:
        f.write(f"""# Synchronized from Stage 0 Sandbox VM (sandbox-hypervisor-node)
TARGET_HOST="{sandbox_ip}"
TARGET_BASE_HOST="{base_host}"
TARGET_USER="{user}"
TARGET_SSH_KEY="{ssh_key}"
TARGET_SSH_PUBKEY="{ssh_pubkey}"
TARGET_LIBVIRT_URI="{libvirt_uri}"
TARGET_STORAGE_POOL="{pool_name}"
TARGET_NETWORK="{net_name}"
TARGET_DEPLOYMENT_MODE="nested-sandbox"
""")

    # 2. Update 01-talos-cluster/terraform.tfvars
    stage1_tfvars_path = os.path.join(REPO_ROOT, "terraform", "environments", "01-talos-cluster", "terraform.tfvars")
    os.makedirs(os.path.dirname(stage1_tfvars_path), exist_ok=True)
    with open(stage1_tfvars_path, "w") as f:
        f.write(f"""# Synchronized from Stage 0 Sandbox VM
libvirt_uri  = "{libvirt_uri}"
storage_pool = "{pool_name}"
network_name = "{net_name}"
""")

    if not quiet:
        print(f"\n  {GREEN}✓ Updated:{RESET} target.env")
        print(f"  {GREEN}✓ Updated:{RESET} terraform/environments/01-talos-cluster/terraform.tfvars")
        print(f"\n{GREEN}{BOLD}🎉 Stage 0 Sandbox VM is now active as the downstream cluster target!{RESET}\n")

    return True


def main():
    parser = argparse.ArgumentParser(description="Synchronize Stage 0 Sandbox Target to Stage 1")
    parser.add_argument("--quiet", action="store_true", help="Suppress non-error output")
    args = parser.parse_args()

    success = sync_sandbox_target(quiet=args.quiet)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
