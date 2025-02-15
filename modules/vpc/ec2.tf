data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  # Filtering the AMI based on name and other properties
  filter {
    name   = "image-id"
    values = ["ami-0c614dee691cbbf37"]
  }

  # Optional: You can define more filters here as needed
}

resource "tls_private_key" "ec2_ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "aws_key_pair" "example" {
  key_name   = "ec2_ssh_key"
  public_key = tls_private_key.ec2_ssh_key.public_key_openssh
}

resource "aws_security_group" "ec2_sg" {
  name_prefix = "ec2-sg"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow EC2 access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name = "ec2-sg"
  }
}


# Create the Secrets Manager Secret
resource "aws_secretsmanager_secret" "private_key_secret" {
  name        = "MyPrivateKeyVault"
  description = "Vault for storing private key"
}

# Store the private key (in PEM format) in the Secret
resource "aws_secretsmanager_secret_version" "private_key_secret_version" {
  secret_id = aws_secretsmanager_secret.private_key_secret.id
  secret_string = jsonencode({
    "ec2_key" : tls_private_key.ec2_ssh_key.private_key_pem
  })
}

resource "aws_launch_template" "api-launch-template" {
  name          = "api-launch-template"
  image_id      = aws_ami.amazon_linux.id # Replace with your AMI ID
  instance_type = "t3.small"              # Specify the instance type
  key_name      = "ec2_ssh_key"           # Replace with your key pair name\


  network_interfaces {
    security_groups = [aws_security_group.ec2_sg.id] # Replace with your security group ID
    subnet_id       = aws_subnet.public[0].id
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "api-instance"
    }
  }

  user_data = base64encode(<<EOF
#!/bin/bash
echo "ECS_CLUSTER=${aws_ecs_cluster.api.name}" >> /etc/ecs/ecs.config
systemctl restart ecs
EOF
  )

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "optional"
  }
}

resource "aws_autoscaling_group" "api-asg" {
  launch_template {
    id      = aws_launch_template.api-launch-template.id
    version = "$Latest"
  }
  #  availability_zones = [aws_subnet.public.availability_zone_id]
  min_size         = 1
  max_size         = 1
  desired_capacity = 1

  health_check_type    = "EC2"
  termination_policies = ["OldestInstance"]
}




