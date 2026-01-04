#!/usr/bin/env python3
"""Update .env file with EC2 auto-start configuration"""
import os
import re

# Configuration
INSTANCE_ID = "i-056dc6971b402f0b2"
AWS_PROFILE = "Cerebrum"
AWS_REGION = "us-east-1"
LLAMA_MODEL = "llama3.2-vision:11b"  # Model installed on EC2 instance

env_file = ".env"

# Read current .env
env_content = []
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        env_content = f.readlines()
else:
    print(f"Creating {env_file}...")

# Track what we've found
found = {
    'EC2_AUTO_START': False,
    'OLLAMA_EC2_INSTANCE_ID': False,
    'AWS_PROFILE': False,
    'AWS_REGION': False,
    'EC2_STARTUP_WAIT_SECONDS': False,
    'EC2_AUTO_SHUTDOWN_MINUTES': False,
    'LLAMA_MODEL': False,
}

# Process existing lines
new_lines = []
for line in env_content:
    line = line.rstrip('\n\r')
    
    if re.match(r'^EC2_AUTO_START=', line):
        new_lines.append(f"EC2_AUTO_START=true\n")
        found['EC2_AUTO_START'] = True
    elif re.match(r'^OLLAMA_EC2_INSTANCE_ID=', line):
        new_lines.append(f"OLLAMA_EC2_INSTANCE_ID={INSTANCE_ID}\n")
        found['OLLAMA_EC2_INSTANCE_ID'] = True
    elif re.match(r'^AWS_PROFILE=', line):
        new_lines.append(f"AWS_PROFILE={AWS_PROFILE}\n")
        found['AWS_PROFILE'] = True
    elif re.match(r'^AWS_REGION=', line):
        new_lines.append(f"AWS_REGION={AWS_REGION}\n")
        found['AWS_REGION'] = True
    elif re.match(r'^EC2_STARTUP_WAIT_SECONDS=', line):
        new_lines.append(f"EC2_STARTUP_WAIT_SECONDS=120\n")
        found['EC2_STARTUP_WAIT_SECONDS'] = True
    elif re.match(r'^EC2_AUTO_SHUTDOWN_MINUTES=', line):
        new_lines.append(f"EC2_AUTO_SHUTDOWN_MINUTES=15\n")
        found['EC2_AUTO_SHUTDOWN_MINUTES'] = True
    elif re.match(r'^LLAMA_MODEL=', line):
        new_lines.append(f"LLAMA_MODEL={LLAMA_MODEL}\n")
        found['LLAMA_MODEL'] = True
    else:
        new_lines.append(line + '\n')

# Add missing settings
if not found['EC2_AUTO_START']:
    new_lines.append(f"EC2_AUTO_START=true\n")
if not found['OLLAMA_EC2_INSTANCE_ID']:
    new_lines.append(f"OLLAMA_EC2_INSTANCE_ID={INSTANCE_ID}\n")
if not found['AWS_PROFILE']:
    new_lines.append(f"AWS_PROFILE={AWS_PROFILE}\n")
if not found['AWS_REGION']:
    new_lines.append(f"AWS_REGION={AWS_REGION}\n")
if not found['EC2_STARTUP_WAIT_SECONDS']:
    new_lines.append(f"EC2_STARTUP_WAIT_SECONDS=120\n")
if not found['EC2_AUTO_SHUTDOWN_MINUTES']:
    new_lines.append(f"EC2_AUTO_SHUTDOWN_MINUTES=15\n")
if not found['LLAMA_MODEL']:
    new_lines.append(f"LLAMA_MODEL={LLAMA_MODEL}\n")

# Check for EC2_AUTO_STOP setting
found_auto_stop = False
for line in env_content:
    if re.match(r'^EC2_AUTO_STOP=', line):
        found_auto_stop = True
        break

if not found_auto_stop:
    new_lines.append(f"EC2_AUTO_STOP=true\n")

# Write updated .env
with open(env_file, 'w') as f:
    f.writelines(new_lines)

print(".env file updated successfully!")
print(f"  EC2_AUTO_START=true")
print(f"  EC2_AUTO_STOP=true")
print(f"  OLLAMA_EC2_INSTANCE_ID={INSTANCE_ID}")
print(f"  AWS_PROFILE={AWS_PROFILE}")
print(f"  AWS_REGION={AWS_REGION}")
print(f"  EC2_AUTO_SHUTDOWN_MINUTES=15")
print(f"  LLAMA_MODEL={LLAMA_MODEL}")

