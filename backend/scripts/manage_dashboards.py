#!/usr/bin/env python3
"""
CloudWatch Dashboard Management Script
Creates, updates, and manages CloudWatch dashboards for the Stock Analysis API
"""
import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.cloudwatch_dashboards import get_dashboard_service, DashboardType, initialize_dashboards


async def create_dashboards():
    """Create all dashboards"""
    print("Creating CloudWatch dashboards...")
    
    service = get_dashboard_service()
    if not service.enabled:
        print("❌ CloudWatch dashboards are disabled. Check your AWS credentials and configuration.")
        return False
    
    results = await service.create_all_dashboards()
    
    print("\nDashboard Creation Results:")
    for dashboard_name, success in results.items():
        status = "✅ Created" if success else "❌ Failed"
        print(f"  {dashboard_name}: {status}")
    
    # Create alarms
    print("\nCreating CloudWatch alarms...")
    alarm_results = await service.create_alarms()
    
    print("\nAlarm Creation Results:")
    for alarm_name, success in alarm_results.items():
        status = "✅ Created" if success else "❌ Failed"
        print(f"  {alarm_name}: {status}")
    
    success_count = sum(results.values()) + sum(alarm_results.values())
    total_count = len(results) + len(alarm_results)
    
    print(f"\n📊 Summary: {success_count}/{total_count} items created successfully")
    return success_count == total_count


async def list_dashboards():
    """List existing dashboards"""
    print("Listing CloudWatch dashboards...")
    
    service = get_dashboard_service()
    if not service.enabled:
        print("❌ CloudWatch dashboards are disabled. Check your AWS credentials and configuration.")
        return
    
    dashboards = await service.list_dashboards()
    
    if dashboards:
        print(f"\nFound {len(dashboards)} Stock Analysis dashboards:")
        for dashboard in dashboards:
            print(f"  📊 {dashboard}")
    else:
        print("\n📭 No Stock Analysis dashboards found")


async def delete_dashboard(dashboard_name: str):
    """Delete a specific dashboard"""
    print(f"Deleting dashboard: {dashboard_name}")
    
    service = get_dashboard_service()
    if not service.enabled:
        print("❌ CloudWatch dashboards are disabled. Check your AWS credentials and configuration.")
        return False
    
    success = await service.delete_dashboard(dashboard_name)
    
    if success:
        print(f"✅ Successfully deleted dashboard: {dashboard_name}")
    else:
        print(f"❌ Failed to delete dashboard: {dashboard_name}")
    
    return success


async def create_specific_dashboard(dashboard_type: str):
    """Create a specific type of dashboard"""
    try:
        dash_type = DashboardType(dashboard_type.lower())
    except ValueError:
        print(f"❌ Invalid dashboard type: {dashboard_type}")
        print(f"Valid types: {', '.join([t.value for t in DashboardType])}")
        return False
    
    print(f"Creating {dash_type.value} dashboard...")
    
    service = get_dashboard_service()
    if not service.enabled:
        print("❌ CloudWatch dashboards are disabled. Check your AWS credentials and configuration.")
        return False
    
    success = await service.create_dashboard(dash_type)
    
    if success:
        print(f"✅ Successfully created {dash_type.value} dashboard")
    else:
        print(f"❌ Failed to create {dash_type.value} dashboard")
    
    return success


def print_dashboard_info():
    """Print information about available dashboards"""
    print("📊 Stock Analysis API - CloudWatch Dashboards")
    print("=" * 50)
    
    print("\n🔧 Operational Dashboard:")
    print("  - API Response Time")
    print("  - Error Rate")
    print("  - Cache Hit Ratio")
    print("  - Cache Operations")
    print("  - System Performance")
    
    print("\n💼 Business Dashboard:")
    print("  - Analysis Completion Rate")
    print("  - Analysis Volume")
    print("  - Analysis Duration")
    print("  - Popular Tickers")
    
    print("\n🚨 Alerting Dashboard:")
    print("  - Error Count by Category")
    print("  - High Response Time Alerts")
    print("  - Failed Analyses")
    print("  - Cache Miss Rate")
    
    print("\n⚠️  CloudWatch Alarms:")
    print("  - High Error Rate (>5%)")
    print("  - High Response Time (>2000ms)")
    print("  - Low Cache Hit Ratio (<70%)")
    print("  - High Analysis Failure Rate (<90% completion)")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Manage CloudWatch dashboards for Stock Analysis API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_dashboards.py create-all          # Create all dashboards and alarms
  python manage_dashboards.py list               # List existing dashboards
  python manage_dashboards.py create operational # Create operational dashboard
  python manage_dashboards.py delete StockAnalysis-Operational
  python manage_dashboards.py info               # Show dashboard information
        """
    )
    
    parser.add_argument(
        'action',
        choices=['create-all', 'list', 'create', 'delete', 'info'],
        help='Action to perform'
    )
    
    parser.add_argument(
        'target',
        nargs='?',
        help='Dashboard type (for create) or dashboard name (for delete)'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    if args.action == 'info':
        print_dashboard_info()
        return
    
    if args.action == 'create-all':
        success = await create_dashboards()
        sys.exit(0 if success else 1)
    
    elif args.action == 'list':
        await list_dashboards()
    
    elif args.action == 'create':
        if not args.target:
            print("❌ Dashboard type required for create action")
            print(f"Available types: {', '.join([t.value for t in DashboardType])}")
            sys.exit(1)
        
        success = await create_specific_dashboard(args.target)
        sys.exit(0 if success else 1)
    
    elif args.action == 'delete':
        if not args.target:
            print("❌ Dashboard name required for delete action")
            sys.exit(1)
        
        success = await delete_dashboard(args.target)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())