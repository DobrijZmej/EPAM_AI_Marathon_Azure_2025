variable "resource_group_name" {
  description = "The name of the resource group."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "function_app_name" {
  description = "The name of the Azure Function App."
  type        = string
}

variable "storage_account_name" {
  description = "The name of the Storage Account for the Function App."
  type        = string
}

variable "app_insights_name" {
  description = "The name of the Application Insights instance."
  type        = string
}

variable "app_settings" {
  description = "A map of app settings to configure on the Function App."
  type        = map(string)
  default     = {}
}

variable "log_analytics_workspace_id" {
  description = "Workspace ID for Log Analytics."
  type        = string
}

variable "log_analytics_workspace_shared_key" {
  description = "Primary shared key for Log Analytics."
  type        = string
}
