terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Region - Mumbai. Agar tumne 'aws configure' mein alag region diya tha, wahi yahan bhi daalo.
provider "aws" {
  region = var.aws_region
}
