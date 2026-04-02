terraform {
  backend "azurerm" {
    resource_group_name  = "research-tfstate-rg"
    storage_account_name = "research-tfstate"
    container_name       = "tfstate"
    key                  = "production.terraform.tfstate"
  }
}
