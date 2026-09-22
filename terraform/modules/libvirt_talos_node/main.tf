terraform {
  required_version = ">= 1.5.0"
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "0.8.1"
    }
  }
}

# -----------------------------------------------------------------------------
# OS Root Volume (Backed by base Talos image)
# -----------------------------------------------------------------------------

resource "libvirt_volume" "root_disk" {
  name           = "${var.node_name}-root.qcow2"
  pool           = var.storage_pool
  base_volume_id = var.base_volume_id
  size           = var.root_disk_size_bytes
  format         = "qcow2"
}

# -----------------------------------------------------------------------------
# Secondary Unformatted Data Volume for Longhorn CSI (/dev/vdb)
# -----------------------------------------------------------------------------

resource "libvirt_volume" "data_disk" {
  count  = var.data_disk_size_bytes > 0 ? 1 : 0
  name   = "${var.node_name}-data.qcow2"
  pool   = var.storage_pool
  size   = var.data_disk_size_bytes
  format = "qcow2"
}

# -----------------------------------------------------------------------------
# Talos Node Virtual Machine Domain
# -----------------------------------------------------------------------------

resource "libvirt_domain" "node" {
  name   = var.node_name
  memory = var.memory_mb
  vcpu   = var.vcpu_count

  cpu {
    mode = "host-passthrough"
  }

  disk {
    volume_id = libvirt_volume.root_disk.id
  }

  dynamic "disk" {
    for_each = var.data_disk_size_bytes > 0 ? [libvirt_volume.data_disk[0].id] : []
    content {
      volume_id = disk.value
    }
  }

  network_interface {
    network_name   = var.network_name
    mac            = var.mac_address != "" ? var.mac_address : null
    wait_for_lease = true
  }

  console {
    type        = "pty"
    target_port = "0"
    target_type = "serial"
  }

  graphics {
    type        = "vnc"
    listen_type = "address"
    autoport    = true
  }
}
