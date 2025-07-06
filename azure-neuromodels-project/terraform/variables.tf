variable "resource_group_name" {
  description = "The name of the resource group."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "storage_account_name" {
  description = "The name of the Azure Storage account."
  type        = string
}

variable "function_app_name" {
  description = "The name of the Azure Function App."
  type        = string
}

variable "function_storage_account_name" {
  description = "The name of the Storage Account for the Function App."
  type        = string
}

variable "app_insights_name" {
  description = "The name of the Application Insights instance."
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key for LLM"
  type        = string
  sensitive   = true
}