resource "azurerm_log_analytics_workspace" "dialog_metrics" {
  name                = var.log_analytics_workspace_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.dialog_metrics.workspace_id
}

output "log_analytics_workspace_primary_shared_key" {
  value     = azurerm_log_analytics_workspace.dialog_metrics.primary_shared_key
  sensitive = true
}
