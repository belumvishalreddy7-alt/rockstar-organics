output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "database_endpoint" {
  value     = aws_db_instance.main.address
  sensitive = true
}

output "redis_primary_endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "uploads_bucket" {
  value = aws_s3_bucket.uploads.bucket
}

output "backups_bucket" {
  value = aws_s3_bucket.backups.bucket
}

output "acm_certificate_validation_records" {
  description = "Add these DNS records at your registrar/DNS provider to validate the ACM certificate."
  value       = aws_acm_certificate.main.domain_validation_options
}
