#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

try:
    from app.services.batch_processing_service import BatchProcessingService
    print("Import successful!")

    # Test basic functionality
    service = BatchProcessingService()
    print("Service created successfully!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
