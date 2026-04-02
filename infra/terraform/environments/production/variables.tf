variable "location" {
  description = "Azure region"
  type        = string
  default     = "mexicocentral"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "research"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "owner" {
  description = "Resource owner"
  type        = string
}

variable "aks_kubernetes_version" {
  description = "Kubernetes version for AKS"
  type        = string
}

variable "aks_node_vm_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_B2s_v2"
}

variable "aks_node_count" {
  description = "Initial AKS node count"
  type        = number
  default     = 1
}

variable "aks_min_count" {
  description = "Minimum AKS node count"
  type        = number
  default     = 1
}

variable "aks_max_count" {
  description = "Maximum AKS node count"
  type        = number
  default     = 2
}

variable "aks_sku_tier" {
  description = "AKS SKU tier (Free or Standard)"
  type        = string
  default     = "Free"
}

variable "aks_auto_scaling_enabled" {
  description = "Enable AKS cluster autoscaler"
  type        = bool
  default     = false
}

variable "aks_os_disk_size_gb" {
  description = "OS disk size in GB for AKS nodes"
  type        = number
  default     = 30
}

variable "acr_sku" {
  description = "ACR SKU"
  type        = string
  default     = "Basic"
}

variable "vnet_address_space" {
  description = "VNet address space"
  type        = list(string)
  default     = ["10.0.0.0/8"]
}

variable "aks_subnet_prefix" {
  description = "AKS subnet CIDR"
  type        = string
  default     = "10.240.0.0/16"
}

variable "domain_name" {
  description = "Domain name for DNS zone"
  type        = string
  default     = "chiselware.org"
}
