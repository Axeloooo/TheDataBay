output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "aks_cluster_id" {
  description = "AKS cluster resource ID"
  value       = module.aks.cluster_id
}

output "acr_login_server" {
  description = "ACR login server"
  value       = module.acr.login_server
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = module.keyvault.vault_uri
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = module.keyvault.vault_name
}

output "dns_zone_name_servers" {
  description = "DNS zone name servers"
  value       = module.networking.dns_zone_name_servers
}
