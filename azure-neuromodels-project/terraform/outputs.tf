output "function_app_url" {
  description = "URL для Azure Function (API)"
  value = "https://${module.function_app.function_app_default_hostname}"
}

output "static_website_url" {
  description = "URL для статичного веб-сайту (index.html)"
  value = module.static_website.static_website_url
}

output "cosmosdb_account_endpoint" {
  value = module.cosmosdb_serverless.cosmosdb_account_endpoint
}

output "cosmosdb_account_primary_key" {
  value     = module.cosmosdb_serverless.cosmosdb_account_primary_key
  sensitive = true
}

output "text_analytics_endpoint" {
  value = module.cognitive_services.endpoint
}

output "text_analytics_key" {
  value     = module.cognitive_services.primary_key
  sensitive = true
}
