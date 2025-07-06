resource "azurerm_storage_account" "this" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  allow_blob_public_access = false
}

resource "azurerm_storage_container" "knowledge" {
  name                  = "knowledge-base"
  storage_account_name  = azurerm_storage_account.this.name
  container_access_type = "private"
}