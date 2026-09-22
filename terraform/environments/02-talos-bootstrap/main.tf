terraform {
  required_version = ">= 1.5.0"
  required_providers {
    talos = {
      source  = "siderolabs/talos"
      version = ">= 0.6.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.4.0"
    }
  }
}

# -----------------------------------------------------------------------------
# Talos Cluster PKI Secrets & Declarative Machine Configs
# -----------------------------------------------------------------------------

resource "talos_machine_secrets" "this" {
  talos_version = var.talos_version
}

data "talos_client_configuration" "this" {
  cluster_name         = var.cluster_name
  client_configuration = talos_machine_secrets.this.client_configuration
  endpoints            = [var.controlplane_ip]
  nodes                = [var.controlplane_ip, var.worker_01_ip, var.worker_02_ip]
}

data "talos_machine_configuration" "controlplane" {
  cluster_name       = var.cluster_name
  cluster_endpoint   = "https://${var.controlplane_ip}:${var.controlplane_port}"
  machine_type       = "controlplane"
  machine_secrets    = talos_machine_secrets.this.machine_secrets
  talos_version      = var.talos_version
  kubernetes_version = var.kubernetes_version
  config_patches = [
    fileexists("${var.patches_dir}/cilium.yaml") ? file("${var.patches_dir}/cilium.yaml") : ""
  ]
}

data "talos_machine_configuration" "worker" {
  cluster_name       = var.cluster_name
  cluster_endpoint   = "https://${var.controlplane_ip}:${var.controlplane_port}"
  machine_type       = "worker"
  machine_secrets    = talos_machine_secrets.this.machine_secrets
  talos_version      = var.talos_version
  kubernetes_version = var.kubernetes_version
  config_patches = [
    fileexists("${var.patches_dir}/cilium.yaml") ? file("${var.patches_dir}/cilium.yaml") : "",
    fileexists("${var.patches_dir}/longhorn-storage.yaml") ? file("${var.patches_dir}/longhorn-storage.yaml") : ""
  ]
}

# -----------------------------------------------------------------------------
# Apply Machine Configurations over mTLS
# -----------------------------------------------------------------------------

resource "talos_machine_configuration_apply" "controlplane" {
  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.controlplane.machine_configuration
  node                        = var.controlplane_ip
}

resource "talos_machine_configuration_apply" "worker_01" {
  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.worker.machine_configuration
  node                        = var.worker_01_ip
}

resource "talos_machine_configuration_apply" "worker_02" {
  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.worker.machine_configuration
  node                        = var.worker_02_ip
}

# -----------------------------------------------------------------------------
# Bootstrap etcd Quorum
# -----------------------------------------------------------------------------

resource "talos_machine_bootstrap" "this" {
  depends_on           = [talos_machine_configuration_apply.controlplane]
  client_configuration = talos_machine_secrets.this.client_configuration
  node                 = var.controlplane_ip
  endpoint             = var.controlplane_ip
}

# -----------------------------------------------------------------------------
# Extract Admin Kubeconfig & Talosconfig Artifacts
# -----------------------------------------------------------------------------

resource "talos_cluster_kubeconfig" "this" {
  depends_on           = [talos_machine_bootstrap.this]
  client_configuration = talos_machine_secrets.this.client_configuration
  node                 = var.controlplane_ip
  endpoint             = var.controlplane_ip
}

resource "local_file" "kubeconfig" {
  content         = talos_cluster_kubeconfig.this.kubeconfig_raw
  filename        = "${var.output_dir}/kubeconfig"
  file_permission = "0600"
}

resource "local_file" "talosconfig" {
  content         = data.talos_client_configuration.this.talos_config
  filename        = "${var.output_dir}/talos/talosconfig"
  file_permission = "0600"
}
