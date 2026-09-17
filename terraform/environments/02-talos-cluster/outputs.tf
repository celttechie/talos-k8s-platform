output "controlplane_nodes" {
  description = "Summary of control plane node metadata."
  value = {
    name        = module.control_plane_01.node_name
    role        = module.control_plane_01.role
    mac_address = module.control_plane_01.mac_address
    ip_address  = module.control_plane_01.ip_address
  }
}

output "worker_nodes" {
  description = "Summary of worker nodes metadata."
  value = {
    worker_01 = {
      name           = module.worker_01.node_name
      role           = module.worker_01.role
      mac_address    = module.worker_01.mac_address
      ip_address     = module.worker_01.ip_address
      data_volume_id = module.worker_01.data_volume_id
    }
    worker_02 = {
      name           = module.worker_02.node_name
      role           = module.worker_02.role
      mac_address    = module.worker_02.mac_address
      ip_address     = module.worker_02.ip_address
      data_volume_id = module.worker_02.data_volume_id
    }
  }
}

output "cluster_endpoints" {
  description = "Node IP addresses for talosctl generation."
  value = {
    controlplane_ip = module.control_plane_01.ip_address
    worker_01_ip    = module.worker_01.ip_address
    worker_02_ip    = module.worker_02.ip_address
  }
}

