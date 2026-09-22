output "domain_id" {
  description = "Libvirt domain ID of the created Talos node."
  value       = libvirt_domain.node.id
}

output "node_name" {
  description = "Name of the Talos node domain."
  value       = libvirt_domain.node.name
}

output "role" {
  description = "Assigned role of the node."
  value       = var.role
}

output "ip_address" {
  description = "Primary IP address resolved from DHCP."
  value       = length(libvirt_domain.node.network_interface[0].addresses) > 0 ? libvirt_domain.node.network_interface[0].addresses[0] : "pending-dhcp"
}

output "mac_address" {
  description = "MAC address assigned to the network interface."
  value       = libvirt_domain.node.network_interface[0].mac
}

output "root_volume_id" {
  description = "ID of the root OS disk volume."
  value       = libvirt_volume.root_disk.id
}

output "data_volume_id" {
  description = "ID of the secondary Longhorn data disk volume if created."
  value       = var.data_disk_size_bytes > 0 ? libvirt_volume.data_disk[0].id : null
}
