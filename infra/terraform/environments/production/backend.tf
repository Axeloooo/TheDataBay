terraform {
  backend "azurerm" {
    resource_group_name  = "thedatabay-tfstate-rg"
    storage_account_name = "thedatabaytfstate"
    container_name       = "tfstate"
    key                  = "production.terraform.tfstate"
  }
}
