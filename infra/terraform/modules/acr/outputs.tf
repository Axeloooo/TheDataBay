output "login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.main.login_server
}

output "registry_id" {
  description = "ACR resource ID"
  value       = azurerm_container_registry.main.id
}
