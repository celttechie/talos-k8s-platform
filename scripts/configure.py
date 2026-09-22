#!/usr/bin/env python3
"""
Talos Kubernetes Platform - Target Configuration & Verification Wizard
Guides the developer through setting, verifying, and persisting the deployment target.
Generates target.env and terraform.tfvars files upon successful connectivity validation.
"""

import argparse
import os
import re
import subprocess
import sys

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def parse_ssh_config(host_alias, ssh_config_path=None):
    """Extract host configuration from ~/.ssh/config for a specific host alias.

    Raises:
        ValueError: If host_alias is empty or not specified.
        FileNotFoundError: If ssh_config_path does not exist.
        KeyError: If no configuration block is found for host_alias.
    """
    if not host_alias or not str(host_alias).strip():
        raise ValueError("A host alias must be specified.")

    host_alias = str(host_alias).strip()

    if ssh_config_path is None:
        ssh_config_path = os.path.expanduser("~/.ssh/config")

    if not os.path.exists(ssh_config_path):
        raise FileNotFoundError(f"SSH config file not found at '{ssh_config_path}'.")

    with open(ssh_config_path, "r") as f:
        content = f.read()

    pattern = r"(?:^|\n)[ \t]*Host[ \t]+(?=[^\n]*\b" + re.escape(host_alias) + r"\b)[^\n]*\n([\s\S]*?)(?=(?:\n[ \t]*Host[ \t]+|\Z))"
    match = re.search(pattern, content, re.IGNORECASE)
    if not match:
        raise KeyError(f"No configuration block found for host alias '{host_alias}' in '{ssh_config_path}'.")

    block = match.group(1)
    hn = re.search(r"^[ \t]*HostName[ \t]+(\S+)", block, re.IGNORECASE | re.MULTILINE)
    usr = re.search(r"^[ \t]*User[ \t]+(\S+)", block, re.IGNORECASE | re.MULTILINE)
    idf = re.search(r"^[ \t]*IdentityFile[ \t]+(\S+)", block, re.IGNORECASE | re.MULTILINE)

    return {
        "host": hn.group(1).strip("\"'") if hn else None,
        "user": usr.group(1).strip("\"'") if usr else None,
        "key": os.path.expanduser(idf.group(1).strip("\"'")) if idf else None
    }

def ensure_ssh_key(key_path=None, key_type="ed25519"):
    """Ensure an SSH private key exists, generating a new key pair if missing."""
    if not key_path:
        key_path = os.path.expanduser(f"~/.ssh/id_{key_type}")
    else:
        key_path = os.path.abspath(os.path.expanduser(key_path))

    pubkey_path = key_path + ".pub"

    if os.path.exists(key_path):
        return key_path, pubkey_path if os.path.exists(pubkey_path) else key_path

    key_dir = os.path.dirname(key_path)
    os.makedirs(key_dir, mode=0o700, exist_ok=True)
    try:
        os.chmod(key_dir, 0o700)
    except OSError:
        pass

    print(f"  {YELLOW}⚠ SSH key '{key_path}' not found. Generating new {key_type} key pair...{RESET}")
    comment = f"talos-k8s-platform@{os.uname().nodename}"
    cmd = ["ssh-keygen", "-t", key_type, "-f", key_path, "-N", "", "-C", comment]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to generate SSH key pair: {res.stderr.strip()}")

    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass

    print(f"  {GREEN}✓ Generated SSH key pair:{RESET} {key_path} ({pubkey_path})")
    return key_path, pubkey_path

def append_ssh_config_entry(host_alias, host, user, key_path, ssh_config_path=None):
    """Append a Host configuration block to ~/.ssh/config."""
    if ssh_config_path is None:
        ssh_config_path = os.path.expanduser("~/.ssh/config")
    else:
        ssh_config_path = os.path.abspath(os.path.expanduser(ssh_config_path))

    ssh_dir = os.path.dirname(ssh_config_path)
    os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
    try:
        os.chmod(ssh_dir, 0o700)
    except OSError:
        pass

    entry = f"""Host {host_alias}
    HostName {host}
    User {user}
    IdentityFile {key_path}
"""
    prefix = "\n" if os.path.exists(ssh_config_path) and os.path.getsize(ssh_config_path) > 0 else ""
    with open(ssh_config_path, "a") as f:
        f.write(prefix + entry)

    try:
        os.chmod(ssh_config_path, 0o600)
    except OSError:
        pass

    print(f"  {GREEN}✓ Added host entry '{host_alias}' to {ssh_config_path}{RESET}")
    return ssh_config_path

def prompt_value(prompt_text, default_val=None):
    """Prompt user for input with an optional default value."""
    if not sys.stdin.isatty():
        if default_val is not None:
            return default_val
        print(f"\n{RED}Error: Input required for '{prompt_text}' in non-interactive terminal.{RESET}")
        sys.exit(1)
    try:
        while True:
            if default_val is not None:
                prompt_str = f"{BOLD}{prompt_text}{RESET} [{default_val}]: "
            else:
                prompt_str = f"{BOLD}{prompt_text}{RESET}: "
            val = input(prompt_str).strip()
            if val:
                return val
            if default_val is not None:
                return default_val
            print(f"  {YELLOW}Value cannot be empty. Please enter a value.{RESET}")
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(1)

def discover_ssh_keys():
    """Discover existing private SSH keys in ~/.ssh directory."""
    ssh_dir = os.path.expanduser("~/.ssh")
    if not os.path.exists(ssh_dir):
        return []

    candidates = []
    standard_names = ["id_ed25519", "id_rsa", "id_ecdsa", "id_dsa"]
    for name in standard_names:
        p = os.path.join(ssh_dir, name)
        if os.path.isfile(p):
            candidates.append(p)

    try:
        for fname in sorted(os.listdir(ssh_dir)):
            full_path = os.path.join(ssh_dir, fname)
            if not os.path.isfile(full_path):
                continue
            if fname.endswith(".pub") or fname.endswith(".bak") or fname in ["config", "known_hosts", "known_hosts.old", "authorized_keys", "allowed_signers"]:
                continue
            if full_path not in candidates:
                if os.path.exists(full_path + ".pub"):
                    candidates.append(full_path)
    except OSError:
        pass

    return candidates

def select_or_create_ssh_key(default_key=None, interactive=True):
    """Interactive / automated selection or creation of SSH private key."""
    if default_key and os.path.exists(os.path.expanduser(default_key)):
        key_path = os.path.abspath(os.path.expanduser(default_key))
        pub_path = key_path + ".pub" if os.path.exists(key_path + ".pub") else key_path
        return key_path, pub_path

    found_keys = discover_ssh_keys()

    if not interactive or not sys.stdin.isatty():
        if found_keys:
            key_path = found_keys[0]
            pub_path = key_path + ".pub" if os.path.exists(key_path + ".pub") else key_path
            return key_path, pub_path
        return ensure_ssh_key()

    print(f"\n{BLUE}===> Select SSH Private Key for Authentication:{RESET}")
    options = []
    for i, k in enumerate(found_keys, 1):
        ktype = "ed25519" if "ed25519" in k else ("rsa" if "rsa" in k else "key")
        options.append(k)
        print(f"  [{i}] {k} ({ktype})")

    gen_opt_num = len(options) + 1
    custom_opt_num = len(options) + 2
    print(f"  [{gen_opt_num}] Generate a new SSH key pair (Ed25519)")
    print(f"  [{custom_opt_num}] Specify a custom key path")

    default_choice = "1" if found_keys else str(gen_opt_num)
    while True:
        choice = prompt_value("Select key option", default_choice)
        if choice.isdigit():
            c_int = int(choice)
            if 1 <= c_int <= len(options):
                selected = options[c_int - 1]
                pub = selected + ".pub" if os.path.exists(selected + ".pub") else selected
                return selected, pub
            elif c_int == gen_opt_num:
                new_key_candidate = os.path.expanduser("~/.ssh/id_ed25519")
                if os.path.exists(new_key_candidate):
                    new_key_candidate = os.path.expanduser("~/.ssh/id_talos_ed25519")
                new_key_path = prompt_value("New SSH Private Key Path", new_key_candidate)
                return ensure_ssh_key(new_key_path)
            elif c_int == custom_opt_num:
                custom_path = prompt_value("Enter SSH Private Key Path")
                return ensure_ssh_key(custom_path)
        print(f"  {YELLOW}Invalid selection. Please choose an option between 1 and {custom_opt_num}.{RESET}")

def verify_target(host, user, key_path, pubkey_path, pool_name, net_name):
    """Perform live validation against the target server."""
    print(f"\n{BLUE}===> Verifying connectivity & hypervisor prerequisites on {host}...{RESET}")

    ssh_opts = ["ssh", "-o", "ConnectTimeout=4", "-o", "StrictHostKeyChecking=no", "-i", key_path, f"{user}@{host}"]

    # 1. SSH Handshake
    res = subprocess.run(ssh_opts + ["hostname"], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  {RED}✗ SSH Connection Failed:{RESET} {res.stderr.strip()}")
        if pubkey_path and os.path.exists(pubkey_path):
            print(f"\n  {YELLOW}Tip: Ensure your public key is authorized on the remote server:{RESET}")
            print(f"    {BOLD}ssh-copy-id -i {pubkey_path} {user}@{host}{RESET}\n")
        return False, None
    remote_hostname = res.stdout.strip()
    print(f"  {GREEN}✓ SSH Handshake Succeeded{RESET} (Remote Host: {BOLD}{remote_hostname}{RESET})")

    # 2. Hardware KVM Passthrough
    res = subprocess.run(ssh_opts + ["[ -e /dev/kvm ] && echo OK || echo MISSING"], capture_output=True, text=True)
    if "OK" not in res.stdout:
        print(f"  {RED}✗ Hardware KVM missing on target server (/dev/kvm not found){RESET}")
        return False, None
    print(f"  {GREEN}✓ Hardware KVM passthrough active{RESET} (/dev/kvm present)")

    # 3. Remote Libvirtd Daemon Responsiveness
    res = subprocess.run(ssh_opts + ["virsh -c qemu:///system list --all >/dev/null 2>&1 && echo OK || echo FAIL"], capture_output=True, text=True)
    if "OK" not in res.stdout:
        print(f"  {RED}✗ Libvirtd daemon unresponsive on target server (qemu:///system){RESET}")
        return False, None
    print(f"  {GREEN}✓ Libvirtd system daemon responsive{RESET}")

    # 4. Storage Pool Verification
    res = subprocess.run(ssh_opts + ["virsh -c qemu:///system pool-list --all"], capture_output=True, text=True)
    if pool_name not in res.stdout:
        print(f"  {YELLOW}⚠ Storage pool '{pool_name}' not listed as active in libvirt{RESET}")
    else:
        print(f"  {GREEN}✓ Storage pool '{pool_name}' active{RESET}")

    # 5. Network Bridge Verification
    res = subprocess.run(ssh_opts + ["virsh -c qemu:///system net-list --all"], capture_output=True, text=True)
    if net_name not in res.stdout:
        print(f"  {YELLOW}⚠ Network bridge '{net_name}' not listed as active in libvirt{RESET}")
    else:
        print(f"  {GREEN}✓ Network bridge '{net_name}' active{RESET}")

    return True, remote_hostname

def write_configs(host, user, key_path, pubkey_path, pool_name, net_name, mac_addr):
    """Write target.env and terraform.tfvars files."""
    libvirt_uri = f"qemu+ssh://{user}@{host}/system?keyfile={key_path}"

    # 1. target.env
    target_env_path = os.path.join(REPO_ROOT, "target.env")
    with open(target_env_path, "w") as f:
        f.write(f"""# Generated by 'make configure'
TARGET_HOST="{host}"
TARGET_USER="{user}"
TARGET_SSH_KEY="{key_path}"
TARGET_SSH_PUBKEY="{pubkey_path}"
TARGET_LIBVIRT_URI="{libvirt_uri}"
TARGET_STORAGE_POOL="{pool_name}"
TARGET_NETWORK="{net_name}"
TARGET_MAC="{mac_addr}"
""")
    print(f"  {GREEN}✓ Generated:{RESET} target.env")

    # 2. Stage 1 terraform.tfvars
    stage1_tfvars_path = os.path.join(REPO_ROOT, "terraform", "environments", "01-nested-sandbox", "terraform.tfvars")
    with open(stage1_tfvars_path, "w") as f:
        f.write(f"""# Generated by 'make configure'
libvirt_uri     = "{libvirt_uri}"
storage_pool    = "{pool_name}"
network_name    = "{net_name}"
mac_address     = "{mac_addr}"
""")
    print(f"  {GREEN}✓ Generated:{RESET} terraform/environments/01-nested-sandbox/terraform.tfvars")

    # 3. Stage 2 terraform.tfvars
    stage2_tfvars_path = os.path.join(REPO_ROOT, "terraform", "environments", "02-talos-cluster", "terraform.tfvars")
    with open(stage2_tfvars_path, "w") as f:
        f.write(f"""# Generated by 'make configure'
libvirt_uri  = "{libvirt_uri}"
storage_pool = "{pool_name}"
network_name = "{net_name}"
""")
    print(f"  {GREEN}✓ Generated:{RESET} terraform/environments/02-talos-cluster/terraform.tfvars")

def main():
    parser = argparse.ArgumentParser(description="Target Server Configuration & Verification Wizard")
    parser.add_argument("--alias", help="SSH host alias in ~/.ssh/config")
    parser.add_argument("--non-interactive", action="store_true", help="Run without prompts using defaults/arguments")
    parser.add_argument("--host", help="Target server IP or hostname")
    parser.add_argument("--user", help="SSH username on target server")
    parser.add_argument("--key", help="Path to SSH private key")
    parser.add_argument("--pool", default="default", help="Libvirt storage pool name (default: default)")
    parser.add_argument("--network", default="default", help="Libvirt network name (default: default)")
    parser.add_argument("--mac", default="52:54:00:BA:67:8E", help="Static MAC reservation for sandbox VM")
    args = parser.parse_args()

    print(f"\n{BLUE}{BOLD}=============================================================================={RESET}")
    print(f"{BLUE}{BOLD}     Talos Kubernetes Platform - Deployment Target Setup Wizard               {RESET}")
    print(f"{BLUE}{BOLD}=============================================================================={RESET}\n")

    # 1. Determine host alias
    if args.alias:
        host_alias = args.alias.strip()
    elif args.non_interactive:
        if args.host:
            host_alias = args.host.strip()
        else:
            print(f"{RED}Error: --alias or --host required in non-interactive mode.{RESET}\n")
            return 1
    else:
        host_alias = prompt_value("Target Server SSH Host Alias (e.g. homelab1, k8s-host, sandbox1)").strip()

    host = args.host
    user = args.user
    key_path = args.key
    pubkey_path = None

    # 2. Check SSH config
    try:
        detected = parse_ssh_config(host_alias)
        print(f"  {GREEN}✓ Found SSH config for '{host_alias}':{RESET} host={detected.get('host')}, user={detected.get('user')}")
        host = host or detected.get("host") or host_alias
        user = user or detected.get("user") or os.getenv("USER", "root")
        detected_key = detected.get("key")
        if not key_path:
            if detected_key and os.path.exists(detected_key):
                key_path = detected_key
                pubkey_path = key_path + ".pub" if os.path.exists(key_path + ".pub") else key_path
            else:
                key_path, pubkey_path = select_or_create_ssh_key(default_key=detected_key, interactive=not args.non_interactive)
    except (FileNotFoundError, KeyError) as e:
        print(f"  {YELLOW}ℹ {e}{RESET}")
        if args.non_interactive:
            if not host:
                print(f"\n{RED}Error: Host alias '{host_alias}' not configured in ~/.ssh/config and --host not specified.{RESET}\n")
                return 1
            user = user or os.getenv("USER", "root")
            if not key_path:
                key_path, pubkey_path = select_or_create_ssh_key(interactive=False)
            else:
                key_path, pubkey_path = ensure_ssh_key(key_path)
            append_ssh_config_entry(host_alias, host, user, key_path)
        else:
            print(f"\n{BLUE}===> Setting up SSH configuration for alias '{host_alias}'...{RESET}")
            host = host or prompt_value(f"Target Server Hostname or IP for '{host_alias}'")
            user = user or prompt_value("SSH Username", os.getenv("USER", "root"))
            if not key_path:
                key_path, pubkey_path = select_or_create_ssh_key(interactive=True)
            else:
                key_path, pubkey_path = ensure_ssh_key(key_path)
            append_ssh_config_entry(host_alias, host, user, key_path)
    except ValueError as e:
        print(f"\n{RED}Error: {e}{RESET}\n")
        return 1

    if not pubkey_path:
        pubkey_path = key_path + ".pub" if os.path.exists(key_path + ".pub") else key_path

    # 3. Libvirt resource options
    pool_name = args.pool if args.non_interactive else prompt_value("Libvirt Storage Pool", args.pool)
    net_name = args.network if args.non_interactive else prompt_value("Libvirt Network Bridge", args.network)
    mac_addr = args.mac if args.non_interactive else prompt_value("Sandbox VM MAC Address", args.mac)

    # 4. Target verification
    ok, remote_host = verify_target(host, user, key_path, pubkey_path, pool_name, net_name)
    if not ok:
        print(f"\n{RED}{BOLD}Target verification failed. Please correct credentials or connectivity and retry.{RESET}\n")
        return 1

    # 5. Write configurations
    print(f"\n{BLUE}===> Persisting verified target configuration...{RESET}")
    write_configs(host, user, key_path, pubkey_path, pool_name, net_name, mac_addr)

    print(f"\n{GREEN}{BOLD}🎉 Target deployment server '{remote_host}' ({host}) configured & verified!{RESET}")
    print(f"{GREEN}You can now run 'make preflight' or proceed to infrastructure provisioning.{RESET}\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
