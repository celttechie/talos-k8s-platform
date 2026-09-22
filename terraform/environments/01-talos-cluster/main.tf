terraform {
  required_version = ">= 1.5.0"
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "0.8.1"
    }
  }
}

provider "libvirt" {
  uri = var.libvirt_uri
}

# -----------------------------------------------------------------------------
# Base Talos Linux OS Image (KVM / QEMU)
# -----------------------------------------------------------------------------

resource "libvirt_volume" "talos_base_image" {
  name   = "talos-${var.talos_version}-nocloud-amd64.raw"
  pool   = var.storage_pool
  source = var.talos_image_url
  format = "raw"
}

# -----------------------------------------------------------------------------
# Control Plane Node (talos-cp-01)
# -----------------------------------------------------------------------------

module "control_plane_01" {
  source = "../../modules/libvirt_talos_node"

  node_name            = "${var.cluster_name}-cp-01"
  role                 = "controlplane"
  vcpu_count           = var.controlplane_vcpu
  memory_mb            = var.controlplane_memory_mb
  root_disk_size_bytes = var.os_disk_size_bytes
  data_disk_size_bytes = 0 # Control plane does not participate in Longhorn storage pool
  base_volume_id       = libvirt_volume.talos_base_image.id
  storage_pool         = var.storage_pool
  network_name         = var.network_name
  mac_address          = var.controlplane_mac
}

# -----------------------------------------------------------------------------
# Worker Node 01 (talos-worker-01) - with Longhorn data disk (/dev/vdb)
# -----------------------------------------------------------------------------

module "worker_01" {
  source = "../../modules/libvirt_talos_node"

  node_name            = "${var.cluster_name}-worker-01"
  role                 = "worker"
  vcpu_count           = var.worker_vcpu
  memory_mb            = var.worker_memory_mb
  root_disk_size_bytes = var.os_disk_size_bytes
  data_disk_size_bytes = var.longhorn_disk_size_bytes
  base_volume_id       = libvirt_volume.talos_base_image.id
  storage_pool         = var.storage_pool
  network_name         = var.network_name
  mac_address          = var.worker_01_mac
}

# -----------------------------------------------------------------------------
# Worker Node 02 (talos-worker-02) - with Longhorn data disk (/dev/vdb)
# -----------------------------------------------------------------------------

module "worker_02" {
  source = "../../modules/libvirt_talos_node"

  node_name            = "${var.cluster_name}-worker-02"
  role                 = "worker"
  vcpu_count           = var.worker_vcpu
  memory_mb            = var.worker_memory_mb
  root_disk_size_bytes = var.os_disk_size_bytes
  data_disk_size_bytes = var.longhorn_disk_size_bytes
  base_volume_id       = libvirt_volume.talos_base_image.id
  storage_pool         = var.storage_pool
  network_name         = var.network_name
  mac_address          = var.worker_02_mac
}
