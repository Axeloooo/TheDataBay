output "cluster_id" {
  description = "AKS cluster ID"
  value       = azurerm_kubernetes_cluster.main.id
}

output "kube_config_raw" {
  description = "Raw kubeconfig"
  value       = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive   = true
}

output "kubelet_identity_object_id" {
  description = "Kubelet identity object ID"
  value       = try(azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id, null)
}

output "key_vault_secrets_provider_identity_object_id" {
  description = "Key Vault Secrets Provider addon identity object ID"
  value       = try(azurerm_kubernetes_cluster.main.key_vault_secrets_provider[0].secret_identity[0].object_id, null)
}

output "node_resource_group" {
  description = "Auto-generated node resource group"
  value       = azurerm_kubernetes_cluster.main.node_resource_group
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL"
  value       = azurerm_kubernetes_cluster.main.oidc_issuer_url
}
