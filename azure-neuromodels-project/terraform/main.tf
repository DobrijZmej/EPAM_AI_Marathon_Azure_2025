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
  }
}

variable "search_api_key" {
  description = "Admin key for Azure Cognitive Search"
  type        = string
  sensitive   = true
}
