terraform {
    backend "s3" {
        bucket         = "franchise-pipeline-dev-state-lock"
        key            = "terraform.tfstate"
        region         = "ap-southeast-1"
        encrypt        = true
        use_lockfile = true
    }
}