#!/usr/bin/env python3

import ast
import sys
import os

# Add the backend directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

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

    # Try to parse the content as AST instead of executing it
    try:
        tree = ast.parse(content)
        print("File parsed successfully as valid Python!")
        
        # Look for class definitions in the AST
        class_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_names.append(node.name)
        
        if 'BatchProcessingService' in class_names:
            print("BatchProcessingService class found in AST!")
        else:
            print("BatchProcessingService class NOT found in AST!")
            
        print(f"Found classes: {class_names}")
        
    except SyntaxError as e:
        print(f"Syntax error in file: {e}")
        print(f"Error at line {e.lineno}: {e.text}")
    except Exception as e:
        print(f"Error parsing file: {e}")
        import traceback
        traceback.print_exc()
