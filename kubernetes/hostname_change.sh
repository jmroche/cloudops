#!/bin/bash

ec2id=$(curl http://169.254.169.254/latest/meta-data/instance-id)
hostname=$(aws ec2 describe-tags --filters "Name=resource-id,Values=$ec2id" "Name=key,Values=Name" --region us-east-1 | awk '/"Value":/ {print $2}' | tr -d '",')
fqdn="${hostname}.local"

cat >/etc/hosts <<EOF
# The following lines are desirable for IPv4 capable hosts
127.0.0.1 ${fqdn} ${hostname}
127.0.0.1 localhost.localdomain localhost
127.0.0.1 localhost4.localdomain4 localhost4
# The following lines are desirable for IPv6 capable hosts
::1 ${fqdn} ${hostname}
::1 localhost.localdomain localhost
::1 localhost6.localdomain6 localhost6
EOF

echo "preserve_hostname: true" >> /etc/cloud/cloud.cfg
hostnamectl set-hostname ${hostname}.localdomain
reboot

https://github.com/calvintrobinson/AWS-Hostname-Change-Based-on-Tag-Scripts