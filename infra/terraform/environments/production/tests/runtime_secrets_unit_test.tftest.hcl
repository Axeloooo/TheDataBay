mock_provider "azurerm" {
  mock_data "azurerm_client_config" {
    defaults = {
      object_id = "00000000-0000-0000-0000-000000000000"
      tenant_id = "11111111-1111-1111-1111-111111111111"
    }
  }

  mock_resource "azurerm_container_registry" {
    defaults = {
      id           = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.ContainerRegistry/registries/thedatabay"
      login_server = "thedatabay.azurecr.io"
    }
  }

  mock_resource "azurerm_dns_zone" {
    defaults = {
      id           = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.Network/dnsZones/thedatabay.com"
      name_servers = ["ns1.example.test."]
    }
  }

  mock_resource "azurerm_key_vault" {
    defaults = {
      id        = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.KeyVault/vaults/thedatabay-production-kv"
      name      = "thedatabay-production-kv"
      vault_uri = "https://thedatabay-production-kv.vault.azure.net/"
    }
  }

  mock_resource "azurerm_kubernetes_cluster" {
    defaults = {
      id                  = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.ContainerService/managedClusters/thedatabay-production-aks"
      kube_config_raw     = ""
      kubelet_identity    = [{ object_id = "22222222-2222-2222-2222-222222222222" }]
      node_resource_group = "mc_mock"
      oidc_issuer_url     = "https://issuer.example.test/"
      key_vault_secrets_provider = [{
        secret_identity = [{ object_id = "33333333-3333-3333-3333-333333333333" }]
      }]
    }
  }

  mock_resource "azurerm_resource_group" {
    defaults = {
      id = "/subscriptions/mock/resourceGroups/thedatabay-production-rg"
    }
  }

  mock_resource "azurerm_role_assignment" {
    defaults = {
      id = "/subscriptions/mock/providers/Microsoft.Authorization/roleAssignments/00000000-0000-0000-0000-000000000000"
    }
  }

  mock_resource "azurerm_subnet" {
    defaults = {
      id = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.Network/virtualNetworks/thedatabay/subnets/aks-subnet"
    }
  }

  mock_resource "azurerm_virtual_network" {
    defaults = {
      id = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.Network/virtualNetworks/thedatabay"
    }
  }
}

variables {
  aks_kubernetes_version = "1.33"
  owner                  = "platform-test"
}

override_module {
  target = module.acr

  outputs = {
    login_server = "thedatabay.azurecr.io"
    registry_id  = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.ContainerRegistry/registries/thedatabay"
  }
}

override_module {
  target = module.aks

  outputs = {
    cluster_id                                    = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.ContainerService/managedClusters/thedatabay-production-aks"
    key_vault_secrets_provider_identity_object_id = "33333333-3333-3333-3333-333333333333"
    kube_config_raw                               = ""
    kubelet_identity_object_id                    = "22222222-2222-2222-2222-222222222222"
    node_resource_group                           = "mc_mock"
    oidc_issuer_url                               = "https://issuer.example.test/"
  }
}

override_module {
  target = module.keyvault

  outputs = {
    vault_id   = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.KeyVault/vaults/thedatabay-production-kv"
    vault_name = "thedatabay-production-kv"
    vault_uri  = "https://thedatabay-production-kv.vault.azure.net/"
  }
}

override_module {
  target = module.networking

  outputs = {
    aks_subnet_id         = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.Network/virtualNetworks/thedatabay/subnets/aks-subnet"
    dns_zone_id           = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.Network/dnsZones/thedatabay.com"
    dns_zone_name_servers = ["ns1.example.test."]
    vnet_id               = "/subscriptions/mock/resourceGroups/mock/providers/Microsoft.Network/virtualNetworks/thedatabay"
  }
}

run "runtime_secret_names_use_llm_configuration" {
  command = plan

  assert {
    condition = alltrue([
      contains(output.runtime_secret_names, "LLM-PROVIDER"),
      contains(output.runtime_secret_names, "LLM-BASE-URL"),
      contains(output.runtime_secret_names, "LLM-CHAT-MODEL"),
      contains(output.runtime_secret_names, "LLM-EMBEDDING-MODEL"),
      contains(output.runtime_secret_names, "LLM-EMBEDDING-DIMENSION"),
      contains(output.runtime_secret_names, "LLM-THINK"),
      contains(output.runtime_secret_names, "DATASET-SUMMARY-COUNT"),
      contains(output.runtime_secret_names, "DATASET-SUMMARY-SAMPLE-ROWS"),
    ])
    error_message = "Runtime secrets must include the LLM and dataset summary configuration names."
  }

  assert {
    condition = alltrue([
      !contains(output.runtime_secret_names, "OLLAMA-HOST"),
      !contains(output.runtime_secret_names, "EMBEDDING-MODEL"),
      !contains(output.runtime_secret_names, "EMBEDDING-DIMENSION"),
      !contains(output.runtime_secret_names, "EMBEDDING-CHUNK-SIZE"),
      !contains(output.runtime_secret_names, "K-ROWS"),
    ])
    error_message = "Runtime secrets must not include retired Ollama, embedding, or K_ROWS names."
  }

  assert {
    condition     = contains(output.optional_runtime_secret_names, "OLLAMA-API-KEY")
    error_message = "OLLAMA-API-KEY must be tracked as an optional runtime secret."
  }
}
