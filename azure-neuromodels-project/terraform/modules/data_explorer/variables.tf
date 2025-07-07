variable "kusto_cluster_name" {
  description = "Name of the Azure Data Explorer (Kusto) cluster"
  type        = string
}

variable "kusto_database_name" {
  description = "Name of the Kusto database"
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
