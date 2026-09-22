variable "cluster_name" {
  description = "Name of the Talos Kubernetes cluster."
  type        = string
  default     = "talos-k8s-platform"
}

variable "talos_version" {
  description = "Talos release version."
  type        = string
  default     = "v1.8.1"
}

variable "kubernetes_version" {
  description = "Kubernetes release version."
  type        = string
  default     = "1.31.0"
}

variable "controlplane_ip" {
  description = "Primary IP address of talos-cp-01."
  type        = string
  default     = "192.168.122.224"
}

variable "controlplane_port" {
  description = "Kubernetes control plane API server port."
  type        = number
  default     = 6443
}

variable "worker_01_ip" {
  description = "Primary IP address of talos-worker-01."
  type        = string
  default     = "192.168.122.241"
}

variable "worker_02_ip" {
  description = "Primary IP address of talos-worker-02."
  type        = string
  default     = "192.168.122.242"
}

variable "patches_dir" {
  description = "Path to custom Talos configuration patch files."
  type        = string
  default     = "../../../talos/patches"
}

variable "output_dir" {
  description = "Path to write output kubeconfig and talosconfig."
  type        = string
  default     = "../../.."
}
