variable "cluster_name" {
  description = "AKS cluster name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "dns_prefix" {
  description = "DNS prefix for the cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
}

variable "node_count" {
  description = "Initial node count"
  type        = number
  default     = 2
}

variable "min_count" {
  description = "Minimum node count for autoscaler"
  type        = number
  default     = 2
}

variable "max_count" {
  description = "Maximum node count for autoscaler"
  type        = number
  default     = 5
}

variable "node_vm_size" {
  description = "VM size for nodes"
  type        = string
  default     = "Standard_B2s"
}

variable "sku_tier" {
  description = "AKS SKU tier (Free or Standard)"
  type        = string
  default     = "Free"
}

variable "auto_scaling_enabled" {
  description = "Enable cluster autoscaler"
  type        = bool
  default     = false
}

variable "os_disk_size_gb" {
  description = "OS disk size in GB for nodes"
  type        = number
  default     = 30
}

variable "subnet_id" {
  description = "Subnet ID for node pool"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
