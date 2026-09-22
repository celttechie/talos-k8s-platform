output "sandbox_vm_id" {
  description = "Unique ID of the sandbox hypervisor domain."
  value       = libvirt_domain.sandbox_hypervisor.id
}

output "sandbox_vm_name" {
  description = "Domain name of the sandbox hypervisor VM."
  value       = libvirt_domain.sandbox_hypervisor.name
}

output "sandbox_ip_address" {
  description = "Primary IP address leased to the sandbox hypervisor VM."
  value       = length(libvirt_domain.sandbox_hypervisor.network_interface[0].addresses) > 0 ? libvirt_domain.sandbox_hypervisor.network_interface[0].addresses[0] : "pending-dhcp"
}

output "sandbox_libvirt_uri" {
  description = "Libvirt TCP connection URI for nested Stage 2 provisioning."
  value       = "qemu+tcp://${length(libvirt_domain.sandbox_hypervisor.network_interface[0].addresses) > 0 ? libvirt_domain.sandbox_hypervisor.network_interface[0].addresses[0] : "localhost"}/system"
}

output "ssh_command" {
  description = "Convenience SSH command to connect to the sandbox hypervisor."
  value       = "ssh ${var.admin_user}@${length(libvirt_domain.sandbox_hypervisor.network_interface[0].addresses) > 0 ? libvirt_domain.sandbox_hypervisor.network_interface[0].addresses[0] : "<sandbox-ip>"}"
}
