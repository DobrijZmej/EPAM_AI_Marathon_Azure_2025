module "data_explorer" {
  source               = "./modules/data_explorer"
  kusto_cluster_name   = "neuromodels-kusto"
  kusto_database_name  = "neuromodelsdb"
  location             = var.location
  resource_group_name  = var.resource_group_name
}
