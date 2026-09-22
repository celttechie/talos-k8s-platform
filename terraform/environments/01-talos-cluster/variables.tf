variable "libvirt_uri" {
  description = "Libvirt connection URI (connects to Stage 1 nested sandbox or local host)."
  type        = string
  default     = "qemu+ssh://bjarrett@192.168.9.110/system?keyfile=/home/bjarrett/.ssh/id_ed25519"
}

variable "cluster_name" {
  description = "Prefix identifier for cluster nodes."
  type        = string
  default     = "talos"
}

variable "talos_version" {
  description = "Talos Linux release version."
  type        = string
  default     = "v1.8.1"
}

variable "talos_image_url" {
  description = "Source URL or local path for the Talos nocloud amd64 disk image (includes iscsi-tools and util-linux-tools for Longhorn)."
  type        = string
  default     = "https://factory.talos.dev/image/613e1592b2da41ae5e265e8789429f22e121aab91cb4deb6bc3c0b6262961245/v1.8.1/nocloud-amd64.raw"
}

variable "storage_pool" {
  description = "Storage pool name on the libvirt hypervisor."
  type        = string
  default     = "default"
}

variable "network_name" {
  description = "Network bridge name on the libvirt hypervisor."
  type        = string
  default     = "default"
}

variable "controlplane_vcpu" {
  description = "vCPU count allocated to the control plane node."
  type        = number
  default     = 2
}

variable "controlplane_memory_mb" {
  description = "Memory allocated to control plane node in MB."
  type        = number
  default     = 4096 # 4 GB
}

variable "worker_vcpu" {
  description = "vCPU count allocated to each worker node."
  type        = number
  default     = 2
}

variable "worker_memory_mb" {
  description = "Memory allocated to each worker node in MB."
  type        = number
  default     = 4096 # 4 GB
}

variable "os_disk_size_bytes" {
  description = "Size of the root OS disk in bytes (default: 20GB)."
  type        = number
  default     = 21474836480 # 20 GB
}

variable "longhorn_disk_size_bytes" {
  description = "Size of secondary unformatted data disk for Longhorn storage in bytes (default: 30GB)."
  type        = number
  default     = 32212254720 # 30 GB
}

variable "controlplane_mac" {
  description = "Optional static MAC address for talos-cp-01."
  type        = string
  default     = "52:54:00:10:00:10"
}

variable "worker_01_mac" {
  description = "Optional static MAC address for talos-worker-01."
  type        = string
  default     = "52:54:00:10:00:21"
}

variable "worker_02_mac" {
  description = "Optional static MAC address for talos-worker-02."
  type        = string
  default     = "52:54:00:10:00:22"
}
