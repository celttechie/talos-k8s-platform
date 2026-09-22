output "talosconfig" {
  description = "Admin talosconfig client configuration."
  value       = data.talos_client_configuration.this.talos_config
  sensitive   = true
}

output "kubeconfig" {
  description = "Admin Kubernetes kubeconfig raw content."
  value       = talos_cluster_kubeconfig.this.kubeconfig_raw
  sensitive   = true
}

output "controlplane_endpoint" {
  description = "Kubernetes control plane API endpoint."
  value       = "https://${var.controlplane_ip}:${var.controlplane_port}"
}
