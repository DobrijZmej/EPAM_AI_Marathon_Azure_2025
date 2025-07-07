terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.70.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

module "blob_storage" {
  source                = "./modules/blob_storage"
  storage_account_name  = "neuromodelsknowledge"
  resource_group_name   = var.resource_group_name
  location              = var.location
}

module "log_analytics" {
  source                      = "./modules/log_analytics"
  log_analytics_workspace_name = "neuromodels-dialog-metrics-eu" # нова унікальна назва
  location                    = "northeurope" # новий регіон
  resource_group_name         = azurerm_resource_group.main.name
}

module "function_app" {
  source                    = "./modules/function_app"
  resource_group_name       = var.resource_group_name
  location                  = var.location
  function_app_name         = var.function_app_name
  storage_account_name      = var.function_storage_account_name
  app_insights_name         = var.app_insights_name
  app_settings = {
    SEARCH_SERVICE_ENDPOINT = "https://neuromodels-search.search.windows.net"
    SEARCH_API_KEY          = var.search_api_key
    SEARCH_INDEX_NAME       = "knowledge-index"
    OPENAI_API_KEY          = var.openai_api_key
    COSMOSDB_ENDPOINT       = module.cosmosdb_serverless.cosmosdb_account_endpoint
    COSMOSDB_KEY            = module.cosmosdb_serverless.cosmosdb_account_primary_key
    COSMOSDB_DATABASE       = "neuromodels-dialogs"
    COSMOSDB_CONTAINER      = "dialog_events"
    TEXT_ANALYTICS_ENDPOINT = module.cognitive_services.endpoint
    TEXT_ANALYTICS_KEY      = module.cognitive_services.primary_key

    # Azure Data Explorer (Kusto) connection for ingest (залишаємо для сумісності)
    KUSTO_INGEST_URI        = var.kusto_ingest_uri
    KUSTO_DB                = var.kusto_db
    KUSTO_TABLE             = var.kusto_table
    KUSTO_INGEST_CLIENT_ID     = var.kusto_ingest_client_id
    KUSTO_INGEST_CLIENT_SECRET = var.kusto_ingest_client_secret
    KUSTO_INGEST_TENANT_ID     = var.kusto_ingest_tenant_id

    # Azure Data Explorer (Kusto) connection for QUERY API (для дешборду)
    KUSTO_CLUSTER        = module.data_explorer.kusto_uri
    KUSTO_DB             = module.data_explorer.kusto_database_name
    KUSTO_CLIENT_ID      = var.kusto_query_client_id
    KUSTO_CLIENT_SECRET  = var.kusto_query_client_secret
    KUSTO_TENANT_ID      = var.kusto_query_tenant_id
  }
  log_analytics_workspace_id        = module.log_analytics.log_analytics_workspace_id
  log_analytics_workspace_shared_key = module.log_analytics.log_analytics_workspace_primary_shared_key
}

module "static_website" {
  source                = "./modules/static_website"
  storage_account_name  = "neuromodelswebdemo"
  resource_group_name   = azurerm_resource_group.main.name
  location              = azurerm_resource_group.main.location
}

module "cosmosdb_serverless" {
  source              = "./modules/cosmosdb_serverless"
  account_name        = "neuromodels-cosmosdb"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  database_name       = "neuromodels-dialogs"
  container_name      = "dialog_events"
}

module "cognitive_services" {
  source              = "./modules/cognitive_services"
  account_name        = "neuromodels-cogsvc"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = {}
}

variable "search_api_key" {
  description = "Admin key for Azure Cognitive Search"
  type        = string
  sensitive   = true
}
