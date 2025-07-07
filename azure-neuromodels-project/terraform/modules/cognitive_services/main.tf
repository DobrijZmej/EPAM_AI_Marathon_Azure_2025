resource "azurerm_cognitive_account" "this" {
  name                = var.account_name
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "TextAnalytics"
  sku_name            = "F0" # або "S"
  tags                = var.tags
  custom_subdomain_name = var.account_name
}

output "endpoint" {
  value = azurerm_cognitive_account.this.endpoint
}

output "primary_key" {
  value     = azurerm_cognitive_account.this.primary_access_key
  sensitive = true
}
