provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    environment = var.environment
    project     = var.project_name
    owner       = var.owner
    managed-by  = "terraform"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "${local.name_prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

module "networking" {
  source = "../../modules/networking"

  vnet_name           = "${local.name_prefix}-vnet"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = var.vnet_address_space
  aks_subnet_prefix   = var.aks_subnet_prefix
  dns_zone_name       = var.domain_name
  tags                = local.common_tags
}

module "aks" {
  source = "../../modules/aks"

  cluster_name         = "${local.name_prefix}-aks"
  location             = azurerm_resource_group.main.location
  resource_group_name  = azurerm_resource_group.main.name
  dns_prefix           = replace(local.name_prefix, "-", "")
  kubernetes_version   = var.aks_kubernetes_version
  node_count           = var.aks_node_count
  min_count            = var.aks_min_count
  max_count            = var.aks_max_count
  node_vm_size         = var.aks_node_vm_size
  sku_tier             = var.aks_sku_tier
  auto_scaling_enabled = var.aks_auto_scaling_enabled
  os_disk_size_gb      = var.aks_os_disk_size_gb
  subnet_id            = module.networking.aks_subnet_id
  tags                 = local.common_tags

  depends_on = [module.networking]
}

module "acr" {
  source = "../../modules/acr"

  registry_name                  = replace("${local.name_prefix}acr", "-", "")
  location                       = azurerm_resource_group.main.location
  resource_group_name            = azurerm_resource_group.main.name
  sku                            = var.acr_sku
  aks_kubelet_identity_object_id = module.aks.kubelet_identity_object_id
  tags                           = local.common_tags

  depends_on = [module.aks]
}

module "keyvault" {
  source = "../../modules/keyvault"

  vault_name                     = "${local.name_prefix}-kv"
  location                       = azurerm_resource_group.main.location
  resource_group_name            = azurerm_resource_group.main.name
  tenant_id                      = data.azurerm_client_config.current.tenant_id
  aks_secrets_provider_object_id = module.aks.key_vault_secrets_provider_identity_object_id
  tags                           = local.common_tags

  depends_on = [module.aks]
}

data "azurerm_client_config" "current" {}
