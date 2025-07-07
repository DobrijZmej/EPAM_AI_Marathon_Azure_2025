resource "azurerm_kusto_cluster" "main" {
  name                = var.kusto_cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku {
    name     = "Standard_D13_v2"
    capacity = 2
  }
}

resource "azurerm_kusto_database" "main" {
  name                = var.kusto_database_name
  resource_group_name = var.resource_group_name
  location            = var.location
  cluster_name        = azurerm_kusto_cluster.main.name
  hot_cache_period    = "P7D"
  soft_delete_period  = "P31D"
}

output "kusto_uri" {
  value = azurerm_kusto_cluster.main.uri
}

output "kusto_database_name" {
  value = azurerm_kusto_database.main.name
}
