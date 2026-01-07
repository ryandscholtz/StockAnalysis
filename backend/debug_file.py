#!/usr/bin/env python3

with open('app/services/batch_processing_service.py', 'r', encoding='utf-8') as f:
    content = f.read()
    print(f"File length: {len(content)}")
    print(f"First 200 chars: {repr(content[:200])}")
    print(f"Last 200 chars: {repr(content[-200:])}")
    
    # Check for the class definition
    if 'class BatchProcessingService' in content:
        print("Class definition found in file!")
    else:
        print("Class definition NOT found in file!")
        
    # Try to execute the content
    try:
        exec(content)
        print("File executed successfully!")
        if 'BatchProcessingService' in locals():
            print("BatchProcessingService is in locals!")
        else:
            print("BatchProcessingService is NOT in locals!")
    except Exception as e:
        print(f"Error executing file: {e}")
        import traceback
        traceback.print_exc()