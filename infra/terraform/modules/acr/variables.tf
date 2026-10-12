variable "registry_name" {
  description = "ACR registry name (globally unique, alphanumeric)"
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

variable "sku" {
  description = "ACR SKU (Basic, Standard, Premium)"
  type        = string
  default     = "Standard"
}

variable "aks_kubelet_identity_object_id" {
  description = "AKS kubelet identity object ID for AcrPull assignment"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
