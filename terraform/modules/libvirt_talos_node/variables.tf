variable "node_name" {
  description = "Unique hostname and domain name for this Talos node."
  type        = string
}

variable "role" {
  description = "Role of the node (controlplane or worker)."
  type        = string
  default     = "worker"
}

variable "memory_mb" {
  description = "Memory allocation in megabytes."
  type        = number
  default     = 3072 # 3 GB
}

variable "vcpu_count" {
  description = "Number of virtual CPUs."
  type        = number
  default     = 2
}

variable "storage_pool" {
  description = "Libvirt storage pool where volumes will be created."
  type        = string
  default     = "default"
}

variable "base_volume_id" {
  description = "Libvirt volume ID of the base Talos OS image."
  type        = string
}

variable "root_disk_size_bytes" {
  description = "Root disk size in bytes (default: 20GB)."
  type        = number
  default     = 21474836480 # 20 GB
}

variable "data_disk_size_bytes" {
  description = "Secondary unformatted data disk size in bytes for Longhorn CSI (0 disables)."
  type        = number
  default     = 0
}

variable "network_name" {
  description = "Libvirt network bridge name."
  type        = string
  default     = "default"
}

variable "mac_address" {
  description = "Optional static MAC address for deterministic DHCP lease assignment."
  type        = string
  default     = ""
}
