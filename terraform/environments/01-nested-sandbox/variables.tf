variable "libvirt_uri" {
  description = "Libvirt connection URI for the L1 host hypervisor."
  type        = string
  default     = "qemu+ssh://bjarrett@192.168.9.110/system?keyfile=/home/bjarrett/.ssh/id_ed25519"
}

variable "vm_name" {
  description = "Hostname and domain name for the L1 Nested Sandbox VM."
  type        = string
  default     = "sandbox-hypervisor-node"
}

variable "memory_mb" {
  description = "Memory allocation in megabytes for the sandbox hypervisor."
  type        = number
  default     = 12288 # 12 GB
}

variable "vcpu_count" {
  description = "Number of virtual CPUs allocated to the sandbox hypervisor."
  type        = number
  default     = 8
}

variable "disk_size_bytes" {
  description = "Root disk size in bytes for the sandbox hypervisor VM."
  type        = number
  default     = 64424509440 # 60 GB
}

variable "storage_pool" {
  description = "Host libvirt storage pool name."
  type        = string
  default     = "default"
}

variable "network_name" {
  description = "Host libvirt network bridge name attaching the sandbox VM."
  type        = string
  default     = "default"
}

variable "cloud_image_url" {
  description = "URL or local path to the Ubuntu cloud image (qcow2)."
  type        = string
  default     = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
}

variable "admin_user" {
  description = "Administrative username configured inside the sandbox VM."
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_key" {
  description = "SSH public key injected for administrative access."
  type        = string
  default     = ""
}

variable "sandbox_network_cidr" {
  description = "Subnet CIDR managed inside the nested sandbox."
  type        = string
  default     = "192.168.124.0/24"
}

variable "mac_address" {
  description = "Static MAC address matching DHCP reservation on host."
  type        = string
  default     = "52:54:00:BA:67:8E"
}
