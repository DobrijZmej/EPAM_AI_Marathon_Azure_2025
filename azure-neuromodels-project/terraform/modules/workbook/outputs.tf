output "workbook_id" {
  description = "The ID of the Azure Monitor Workbook."
  value       = azurerm_monitor_workbook.dialog_analytics.id
}

output "workbook_link" {
  description = "Portal link to the Workbook."
  value       = "https://portal.azure.com/#blade/Microsoft_Azure_Monitoring_Logs/WorkbookBlade/workbookId/${azurerm_monitor_workbook.dialog_analytics.id}"
}
