variable "aws_region" {
  description = "AWS region jahan sab resources banenge"
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "key_pair_name" {
  description = "AWS mein already existing key pair ka naam (SSH ke liye) - AWS Console mein Key Pairs section se naam copy karo"
  type        = string
}

variable "my_ip" {
  description = "Tumhara khud ka public IP, SSH ko sirf isi se allow karne ke liye. Format: x.x.x.x/32"
  type        = string
}
