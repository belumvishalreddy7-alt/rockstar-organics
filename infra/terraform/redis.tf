resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${var.project_name}-redis"
  description                 = "Shared rate-limit / cache store for ${var.project_name}"
  engine                      = "redis"
  engine_version               = "7.1"
  node_type                   = var.redis_node_type
  num_cache_clusters           = var.environment == "production" ? 2 : 1
  automatic_failover_enabled  = var.environment == "production"
  subnet_group_name            = aws_elasticache_subnet_group.main.name
  security_group_ids           = [aws_security_group.data.id]
  at_rest_encryption_enabled  = true
  transit_encryption_enabled  = true
  tags                         = local.tags
}
