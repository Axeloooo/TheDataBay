terraform {
  backend "azurerm" {
    resource_group_name  = "ulenor-tfstate-rg"
    storage_account_name = "ulenortfstate"
    container_name       = "tfstate"
    key                  = "production.terraform.tfstate"
  }
}
