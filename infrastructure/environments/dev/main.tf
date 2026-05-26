locals {
  resource_prefix = "${var.project_name}_${var.environment}"
}

module "base" {
    source = "../../modules/"

    environment = var.environment
    project_name = var.project_name
    aws_region = var.aws_region
}