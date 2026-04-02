output "vnet_id" {
  description = "Virtual network ID"
  value       = azurerm_virtual_network.main.id
}

output "aks_subnet_id" {
  description = "AKS subnet ID"
  value       = azurerm_subnet.aks.id
}

output "dns_zone_id" {
  description = "DNS zone ID (empty string if not created)"
  value       = length(azurerm_dns_zone.main) > 0 ? azurerm_dns_zone.main[0].id : ""
}

output "dns_zone_name_servers" {
  description = "DNS zone name servers"
  value       = length(azurerm_dns_zone.main) > 0 ? azurerm_dns_zone.main[0].name_servers : []
}
