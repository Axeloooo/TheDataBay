terraform {
  backend "azurerm" {
    resource_group_name  = "ip-factory-tfstate-rg"
    storage_account_name = "ipfactorytfstate"
    container_name       = "tfstate"
    key                  = "production.terraform.tfstate"
  }
}
