provider "azurerm" {
  features {}
}

module "networking" {
  source = "./modules/networking"
}

module "blob_storage" {
  source                = "./modules/blob_storage"
  storage_account_name  = "neuromodelsknowledge"
  resource_group_name   = var.resource_group_name
  location              = var.location
}
