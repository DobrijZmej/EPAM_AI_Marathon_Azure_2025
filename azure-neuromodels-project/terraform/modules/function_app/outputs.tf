output "function_app_name" {
  value = azurerm_linux_function_app.this.name
}

output "function_app_default_hostname" {
  value = azurerm_linux_function_app.this.default_hostname
}

output "function_app_id" {
  value = azurerm_linux_function_app.this.id
}

output "app_insights_instrumentation_key" {
  value = azurerm_application_insights.this.instrumentation_key
}
