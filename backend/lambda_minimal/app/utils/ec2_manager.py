"""
EC2 Instance Manager - Auto-start and auto-stop instance for Ollama processing
"""
import os
import boto3
import time
import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class EC2Manager:
    """Manages EC2 instance lifecycle for Ollama processing"""

    def __init__(self):
        self.instance_id = os.getenv("OLLAMA_EC2_INSTANCE_ID", "i-056dc6971b402f0b2")
        self.aws_profile = os.getenv("AWS_PROFILE", "Cerebrum")
        self.aws_region = os.getenv("AWS_REGION", "eu-west-1")
        self.max_startup_wait = int(os.getenv("EC2_STARTUP_WAIT_SECONDS", "120"))  # 2 minutes
        self.auto_shutdown_minutes = int(os.getenv("EC2_AUTO_SHUTDOWN_MINUTES", "15"))  # Shutdown after 15 min idle
        self.auto_stop_enabled = os.getenv("EC2_AUTO_STOP", "true").lower() == "true"

        # Activity tracking for auto-stop
        self.last_activity_time: Optional[datetime] = None
        self.shutdown_task: Optional[asyncio.Task] = None

        # Initialize boto3 session
        try:
            self.session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
            self.ec2 = self.session.client('ec2')
            logger.info(f"EC2Manager initialized for instance {self.instance_id}")
            logger.info(f"Auto-stop: {'ENABLED' if self.auto_stop_enabled else 'DISABLED'} ({self.auto_shutdown_minutes} min idle)")
        except Exception as e:
            logger.warning(f"Failed to initialize EC2 client: {e}. Auto-start will be disabled.")
            self.ec2 = None

    def get_instance_state(self) -> Optional[str]:
        """Get current state of EC2 instance"""
        if not self.ec2:
            return None

        try:
            response = self.ec2.describe_instances(InstanceIds=[self.instance_id])
            if response['Reservations']:
                state = response['Reservations'][0]['Instances'][0]['State']['Name']
                return state
        except ClientError as e:
            logger.error(f"Error checking instance state: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking instance state: {e}")

        return None

    def get_instance_ip(self) -> Optional[str]:
        """Get public IP of EC2 instance"""
        if not self.ec2:
            return None

        try:
            response = self.ec2.describe_instances(InstanceIds=[self.instance_id])
            if response['Reservations']:
                instance = response['Reservations'][0]['Instances'][0]
                state = instance['State']['Name']
                if state == 'running':
                    return instance.get('PublicIpAddress')
        except Exception as e:
            logger.error(f"Error getting instance IP: {e}")

        return None

    def start_instance(self) -> bool:
        """Start EC2 instance and wait for it to be running"""
        if not self.ec2:
            logger.warning("EC2 client not available, cannot start instance")
            return False

        try:
            state = self.get_instance_state()

            if state == 'running':
                logger.info(f"Instance {self.instance_id} is already running")
                return True

            if state == 'stopping' or state == 'stopped':
                logger.info(f"Starting instance {self.instance_id} (current state: {state})...")
                self.ec2.start_instances(InstanceIds=[self.instance_id])

                # Wait for instance to be running
                logger.info(f"Waiting for instance to start (max {self.max_startup_wait}s)...")
                waiter = self.ec2.get_waiter('instance_running')
                waiter.wait(
                    InstanceIds=[self.instance_id],
                    WaiterConfig={'Delay': 5, 'MaxAttempts': self.max_startup_wait // 5}
                )

                # Wait a bit more for Ollama to be ready
                logger.info("Instance is running, waiting for Ollama to be ready...")
                time.sleep(10)  # Give Ollama a moment to start

                logger.info(f"Instance {self.instance_id} started successfully")
                return True
            else:
                logger.warning(f"Instance is in state '{state}', cannot start")
                return False

        except ClientError as e:
            logger.error(f"AWS error starting instance: {e}")
            return False
        except Exception as e:
            logger.error(f"Error starting instance: {e}")
            return False

    def ensure_running(self) -> Optional[str]:
        """
        Ensure instance is running, start if needed.
        Returns the public IP if successful, None otherwise.
        """
        if not self.ec2:
            logger.warning("EC2 client not available")
            return None

        state = self.get_instance_state()

        if state == 'running':
            ip = self.get_instance_ip()
            if ip:
                logger.info(f"Instance is running at {ip}")
                return ip
            else:
                logger.warning("Instance is running but IP not available yet")
                return None

        if state in ['stopped', 'stopping']:
            if self.start_instance():
                ip = self.get_instance_ip()
                if ip:
                    logger.info(f"Instance started successfully at {ip}")
                    return ip
                else:
                    logger.warning("Instance started but IP not available")
                    return None

        logger.warning(f"Instance is in unexpected state: {state}")
        return None

    def record_activity(self):
        """Record that activity occurred (PDF processing, etc.)"""
        self.last_activity_time = datetime.now()
        logger.debug(f"Activity recorded at {self.last_activity_time}")

    def stop_instance(self) -> bool:
        """Stop EC2 instance"""
        if not self.ec2:
            logger.warning("EC2 client not available, cannot stop instance")
            return False

        try:
            state = self.get_instance_state()

            if state == 'stopped' or state == 'stopping':
                logger.info(f"Instance {self.instance_id} is already stopped or stopping")
                return True

            if state == 'running':
                logger.info(f"Stopping instance {self.instance_id}...")
                self.ec2.stop_instances(InstanceIds=[self.instance_id])
                logger.info(f"Instance {self.instance_id} stop initiated")
                self.last_activity_time = None  # Reset activity tracking
                return True
            else:
                logger.warning(f"Instance is in state '{state}', cannot stop")
                return False

        except ClientError as e:
            logger.error(f"AWS error stopping instance: {e}")
            return False
        except Exception as e:
            logger.error(f"Error stopping instance: {e}")
            return False

    async def check_and_stop_if_idle(self):
        """
        Background task to check if instance is idle and stop it.
        Should be called periodically (e.g., every minute).
        """
        if not self.auto_stop_enabled:
            return

        if not self.ec2:
            return

        # Run synchronous boto3 calls in executor to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()

        # Check if instance is running (run in executor since boto3 is sync)
        state = await loop.run_in_executor(None, self.get_instance_state)
        if state != 'running':
            return  # Not running, nothing to do

        # Check if we have activity tracking
        if self.last_activity_time is None:
            # No activity recorded yet, don't stop
            return

        # Calculate idle time
        idle_time = datetime.now() - self.last_activity_time
        idle_minutes = idle_time.total_seconds() / 60

        if idle_minutes >= self.auto_shutdown_minutes:
            logger.info(f"Instance has been idle for {idle_minutes:.1f} minutes (threshold: {self.auto_shutdown_minutes} min). Stopping instance...")
            # Run stop_instance in executor
            stopped = await loop.run_in_executor(None, self.stop_instance)
            if stopped:
                logger.info(f"Instance stopped successfully after {idle_minutes:.1f} minutes of idle time")
            else:
                logger.warning("Failed to stop instance")
        else:
            logger.debug(f"Instance idle for {idle_minutes:.1f} minutes (threshold: {self.auto_shutdown_minutes} min)")

    def schedule_shutdown(self):
        """
        Schedule instance to shutdown after idle period.
        This records activity and starts background monitoring if needed.
        """
        if not self.auto_stop_enabled:
            return

        # Record current activity
        self.record_activity()

        # Start background task if not already running
        if self.shutdown_task is None or self.shutdown_task.done():
            logger.info(f"Auto-stop monitoring active (will stop after {self.auto_shutdown_minutes} min idle)")
            # Note: The actual background task should be started by FastAPI's background tasks
            # This method just records activity


# Global instance
_ec2_manager: Optional[EC2Manager] = None


def get_ec2_manager() -> EC2Manager:
    """Get or create EC2Manager instance"""
    global _ec2_manager
    if _ec2_manager is None:
        _ec2_manager = EC2Manager()
    return _ec2_manager
