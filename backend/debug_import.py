#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

try:
    import app.services.batch_processing_service as batch_module
    print("Module imported successfully!")
    print("Module attributes:", dir(batch_module))
    
    if hasattr(batch_module, 'BatchProcessingService'):
        print("BatchProcessingService found!")
    else:
        print("BatchProcessingService NOT found!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()