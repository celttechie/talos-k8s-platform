terraform {
  required_version = ">= 1.5.0"
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "0.8.1"
    }
    template = {
      source  = "hashicorp/template"
      version = ">= 2.2.0"
    }
  }
}

provider "libvirt" {
  uri = var.libvirt_uri
}

# -----------------------------------------------------------------------------
# OS Root Volume & Cloud-Init Disk
# -----------------------------------------------------------------------------

resource "libvirt_volume" "root_disk" {
  name   = "${var.vm_name}-root.qcow2"
  pool   = var.storage_pool
  source = var.cloud_image_url
  format = "qcow2"

  provisioner "local-exec" {
    command = "virsh -c ${var.libvirt_uri} vol-resize --pool ${var.storage_pool} ${var.vm_name}-root.qcow2 ${var.disk_size_bytes}B"
  }
}

data "template_file" "user_data" {
  template = file("${path.module}/cloud_init.cfg")
  vars = {
    hostname        = var.vm_name
    admin_user      = var.admin_user
    ssh_public_key  = var.ssh_public_key != "" ? var.ssh_public_key : (fileexists(pathexpand("~/.ssh/id_ed25519.pub")) ? file(pathexpand("~/.ssh/id_ed25519.pub")) : (fileexists(pathexpand("~/.ssh/id_rsa.pub")) ? file(pathexpand("~/.ssh/id_rsa.pub")) : ""))
    sandbox_network = var.sandbox_network_cidr
  }
}

resource "libvirt_cloudinit_disk" "commoninit" {
  name      = "${var.vm_name}-cloudinit.iso"
  pool      = var.storage_pool
  user_data = data.template_file.user_data.rendered
}

# -----------------------------------------------------------------------------
# L1 Sandbox Hypervisor Domain (Nested KVM Passthrough)
# -----------------------------------------------------------------------------

resource "libvirt_domain" "sandbox_hypervisor" {
  name   = var.vm_name
  memory = var.memory_mb
  vcpu   = var.vcpu_count

  # CPU host-passthrough is required to expose /dev/kvm hardware virtualization to L1 VM
  cpu {
    mode = "host-passthrough"
  }

  cloudinit = libvirt_cloudinit_disk.commoninit.id

  disk {
    volume_id = libvirt_volume.root_disk.id
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
