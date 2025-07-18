resource "azurerm_storage_account" "function" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_application_insights" "this" {
  name                = var.app_insights_name
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
}

resource "azurerm_service_plan" "function" {
  name                = "${var.function_app_name}-plan"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = "Y1" # Consumption plan
}

resource "azurerm_linux_function_app" "this" {
  name                       = var.function_app_name
  location                   = var.location
  resource_group_name        = var.resource_group_name
  service_plan_id            = azurerm_service_plan.function.id
  storage_account_name       = azurerm_storage_account.function.name
  storage_account_access_key = azurerm_storage_account.function.primary_access_key
  https_only                 = true
  site_config {
    application_stack {
      python_version = "3.11"
    }
    cors {
      allowed_origins = [
        "https://neuromodelswebdemo.z6.web.core.windows.net",
        "https://portal.azure.com",
        "*"
      ]
      support_credentials = false
    }
  }
  app_settings = merge({
    "FUNCTIONS_WORKER_RUNTIME" = "python"
    "WEBSITE_RUN_FROM_PACKAGE" = "1"
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.this.instrumentation_key
    "LOG_ANALYTICS_WORKSPACE_ID" = var.log_analytics_workspace_id
    "LOG_ANALYTICS_SHARED_KEY" = var.log_analytics_workspace_shared_key
    "LOG_ANALYTICS_LOG_TYPE" = "CustomDialogMetrics"
  }, var.app_settings)
}
