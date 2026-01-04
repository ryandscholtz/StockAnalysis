"""
Script to stop the EC2 instance used for Ollama
Run this to stop the instance and avoid charges
"""
import os
import boto3
import sys
from botocore.exceptions import ClientError

def stop_ec2_instance():
    """Stop the EC2 instance"""
    instance_id = os.getenv("OLLAMA_EC2_INSTANCE_ID", "i-056dc6971b402f0b2")
    aws_profile = os.getenv("AWS_PROFILE", "Cerebrum")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    try:
        # Initialize boto3 session
        session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
        ec2 = session.client('ec2')
        
        print(f"Checking EC2 instance {instance_id}...")
        
        # Get current state
        response = ec2.describe_instances(InstanceIds=[instance_id])
        if not response['Reservations']:
            print(f"Instance {instance_id} not found")
            return False
        
        instance = response['Reservations'][0]['Instances'][0]
        state = instance['State']['Name']
        
        print(f"Current state: {state}")
        
        if state == 'stopped' or state == 'stopping':
            print(f"Instance is already stopped or stopping")
            return True
        
        if state == 'running':
            print(f"Stopping instance {instance_id}...")
            ec2.stop_instances(InstanceIds=[instance_id])
            print("Stop command sent successfully")
            print(f"Instance will stop shortly. You can verify with:")
            print(f"  aws ec2 describe-instances --instance-ids {instance_id} --profile {aws_profile} --region {aws_region}")
            return True
        else:
            print(f"Instance is in state '{state}', cannot stop")
            return False
            
    except ClientError as e:
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("EC2 Instance Stopper")
    print("=" * 60)
    print()
    
    success = stop_ec2_instance()
    
    if success:
        print()
        print("=" * 60)
        print("EC2 instance stop initiated successfully")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("Failed to stop EC2 instance")
        print("=" * 60)
        sys.exit(1)

