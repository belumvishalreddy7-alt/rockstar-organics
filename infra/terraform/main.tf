terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  # Fill in a real remote backend before first use - a local state file is
  # not safe for a team or for CI to apply against.
  backend "s3" {
    bucket         = "REPLACE_ME-rockstar-organics-tfstate"
    key            = "rockstar-organics/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "REPLACE_ME-rockstar-organics-tflock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_availability_zones" "available" {
  state = "available"
}
