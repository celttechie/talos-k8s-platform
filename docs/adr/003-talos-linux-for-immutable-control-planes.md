# ADR 003: Talos Linux for Immutable Kubernetes Control Planes

## Status
Accepted

## Context
Traditional general-purpose Linux distributions (e.g., Ubuntu, Debian) include full user spaces, shell access, systemd, package managers, and open SSH ports. This creates configuration drift, broad security attack surfaces, and manual debugging anti-patterns that conflict with immutable infrastructure standards.

## Decision
We select **Talos Linux** as the operating system for all Kubernetes control plane and worker nodes:
1. **API-Driven OS**: Talos has no interactive shell, SSH daemon, or console login. All operations (disk management, network configuration, kernel parameters, upgrades) are driven via mTLS-authenticated gRPC APIs using `talosctl`.
2. **Immutable Read-Only Root Filesystem**: System files are mounted read-only and ephemeral, eliminating configuration drift across reboots.
3. **Declarative Machine Configuration**: Machine definitions are authored in YAML (`controlplane.yaml`, `worker.yaml`), version-controlled in Git, and applied atomically.

## Consequences
- **Positive:** Hardened zero-trust posture with minimal attack surface.
- **Positive:** Eliminates manual "SSH-and-fix" anti-patterns in favor of pure Infrastructure-as-Code.
- **Positive:** Automated upstream Kubernetes lifecycle management directly through Talos APIs.
- **Trade-off:** Requires developers to use `talosctl` tooling and logs rather than traditional Linux terminal commands for node diagnostics.
