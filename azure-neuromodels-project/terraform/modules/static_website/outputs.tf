output "static_website_url" {
  value = azurerm_storage_account.static.primary_web_endpoint
}
