variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short name used to prefix/tag every resource."
  type        = string
  default     = "rockstar-organics"
}

variable "environment" {
  description = "Deployment environment name (production, staging, ...)."
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "domain_name" {
  description = "Public domain the ALB/ACM certificate will serve (e.g. app.rockstarorganics.example)."
  type        = string
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.small"
}

variable "db_name" {
  type    = string
  default = "rockstar_organics"
}

variable "db_username" {
  type    = string
  default = "rso_user"
}

variable "db_password" {
  description = <<-EOT
    RDS master password. Do NOT put a real secret in terraform.tfvars or
    commit it - either pass it via TF_VAR_db_password from a secrets
    manager/CI secret at apply time, or (recommended) switch this
    resource to `manage_master_user_password = true` in database.tf and
    let AWS Secrets Manager generate/rotate it instead.
  EOT
  type        = string
  sensitive   = true
  default     = null
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.micro"
}

variable "backend_container_image" {
  description = "Backend image URI (pushed by .github/workflows/ci.yml)."
  type        = string
}

variable "frontend_container_image" {
  description = "Frontend image URI (pushed by .github/workflows/ci.yml)."
  type        = string
}

variable "backend_desired_count" {
  type    = number
  default = 3
}

variable "sentry_dsn" {
  description = "Sentry DSN for backend error tracking. Empty string disables it."
  type        = string
  default     = ""
  sensitive   = true
}
