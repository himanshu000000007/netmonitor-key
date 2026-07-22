output "public_ip" {
  description = "EC2 server ka public IP - isi se browser mein access karoge"
  value       = aws_instance.netmonitor_server.public_ip
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.netmonitor_server.id
}

output "ssh_command" {
  description = "Server par SSH karne ka ready-made command"
  value       = "ssh -i your-key.pem ubuntu@${aws_instance.netmonitor_server.public_ip}"
}
