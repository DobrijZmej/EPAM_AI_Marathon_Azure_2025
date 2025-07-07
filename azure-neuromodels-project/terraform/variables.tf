variable "kusto_ingest_uri" {
  description = "Kusto ingest URI (e.g. https://<clustername>.<region>.kusto.windows.net)"
  type        = string
}

variable "kusto_db" {
  description = "Kusto database name (e.g. neuromodelsdb)"
  type        = string
}

variable "kusto_table" {
  description = "Kusto table name (e.g. DialogMetrics)"
  type        = string
}

variable "kusto_ingest_client_id" {
  description = "Client ID for Kusto ingest (Service Principal)"
  type        = string
  sensitive   = true
}

variable "kusto_ingest_client_secret" {
  description = "Client Secret for Kusto ingest (Service Principal)"
  type        = string
  sensitive   = true
}

variable "kusto_ingest_tenant_id" {
  description = "Tenant ID for Kusto ingest (Azure AD)"
  type        = string
  sensitive   = true
}
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

variable "kusto_query_client_id" {
  description = "Client ID for Kusto query (Service Principal)"
  type        = string
  sensitive   = true
}

variable "kusto_query_client_secret" {
  description = "Client Secret for Kusto query (Service Principal)"
  type        = string
  sensitive   = true
}

variable "kusto_query_tenant_id" {
  description = "Tenant ID for Kusto query (Azure AD)"
  type        = string
  sensitive   = true
}