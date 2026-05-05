variable "vault_name" {
  description = "Key Vault name (globally unique, 3-24 chars)"
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

variable "tenant_id" {
  description = "Azure tenant ID"
  type        = string
}

variable "aks_secrets_provider_object_id" {
  description = "AKS Key Vault Secrets Provider addon identity object ID"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
