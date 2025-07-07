variable "resource_group_name" {
  description = "The name of the resource group."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "account_name" {
  description = "The name of the Cognitive Services account."
  type        = string
}

variable "tags" {
  description = "Tags for the resource."
  type        = map(string)
  default     = {}
}
