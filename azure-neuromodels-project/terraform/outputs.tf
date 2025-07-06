output "compute_instance_id" {
  value = module.compute.instance_id
}

output "storage_account_name" {
  value = module.storage.account_name
}

output "network_security_group_id" {
  value = module.networking.security_group_id
}

output "public_ip_address" {
  value = module.networking.public_ip
}