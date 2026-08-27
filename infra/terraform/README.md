# Terraform - AWS reference deployment

This is a starting skeleton for a real AWS deployment (ECS Fargate for the
app, RDS Postgres, ElastiCache Redis, S3 for uploads/backups, an ALB with
ACM TLS). It is deliberately not "one `terraform apply` away from
production" — no Terraform skeleton honestly is, since it depends on your
AWS account, existing VPC layout, domain, and compliance requirements. What
it does give you is a real, wired module layout rather than a placeholder.

## Layout

- `main.tf` — providers, backend state config (fill in your S3
  bucket/DynamoDB lock table before first use).
- `variables.tf` — every input this configuration needs.
- `network.tf` — VPC, public/private subnets, NAT gateway, security groups.
- `database.tf` — RDS PostgreSQL (Multi-AZ, encrypted, automated backups).
- `redis.tf` — ElastiCache Redis (for the shared rate limiter).
- `storage.tf` — S3 buckets for uploads and for `ops/backups` output.
- `ecs.tf` — ECS Fargate cluster, task definitions, services, ALB, and
  autoscaling for the backend/frontend containers built by
  `.github/workflows/ci.yml`.
- `outputs.tf` — connection strings/URLs to feed into
  `infra/k8s/secret.example.yaml` or ECS task environment variables.

## Before you `terraform apply`

1. Create the remote state bucket + DynamoDB lock table referenced in
   `main.tf`, or switch to your organization's existing Terraform Cloud/
   remote backend.
2. Fill in `terraform.tfvars` (see `variables.tf` for the full list) —
   at minimum: `aws_region`, `vpc_cidr`, `domain_name`, `db_password`
   (or better, wire this to AWS Secrets Manager instead of a plain
   variable — see `variables.tf`'s comment on `db_password`).
3. Run `terraform init && terraform plan` and read the plan before
   `terraform apply`. This skeleton provisions real billable
   infrastructure (RDS, ElastiCache, NAT gateway, ALB) — nothing in it is
   free-tier by default.
4. Point the container images ECS pulls at the ones
   `.github/workflows/ci.yml` pushes to your registry (update
   `ecs.tf`'s `image` values or, better, drive them from a CI-provided
   tag via a `container_image_tag` variable).
