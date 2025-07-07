variable "log_analytics_workspace_name" {
  description = "Name of the Log Analytics Workspace for dialog metrics"
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group."
  type        = string
}
