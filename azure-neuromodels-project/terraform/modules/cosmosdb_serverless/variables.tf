variable "account_name" {
  description = "Cosmos DB account name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "database_name" {
  description = "Cosmos DB database name"
  type        = string
}

variable "container_name" {
  description = "Cosmos DB container name"
  type        = string
}
