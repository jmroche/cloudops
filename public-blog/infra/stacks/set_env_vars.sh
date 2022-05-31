#!/bin/bash

FILE="/home/ec2-user/.bashrc"

output=$(python3 /home/ec2-user/get_secrets.py)
echo "${output}" >> $FILE
