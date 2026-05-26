variable "aws_region" {
    type = string
    description = "Region Infrastruktur AWS yang dideploy"
    default = "ap-southeast-1" # singapore
}

variable "environment" {
    type = string
    description = "Environment terraform (hanya menerima dev, staging, prod)"

    # Validation production grade
    validation {
        condition = contains(["dev","staging","prod"],var.environment)
        error_message = "Variabel environment harus bernilai 'dev', 'staging', atau 'prod'"
    }
}

variable "project_name" {
    type = string
    description = "Nama project yang akan digunakan"
    default = "franchise-pipeline"
}