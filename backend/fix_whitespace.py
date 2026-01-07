#!/usr/bin/env python3
"""
Script to fix whitespace issues in Python files.
"""
import os
import sys

def fix_whitespace_issues(file_path):
    """Fix various whitespace issues in a Python file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Fix trailing whitespace (W291)
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]

    # Remove blank lines with whitespace (W293)
    lines = [line if line.strip() else '' for line in lines]

    # Ensure file ends with newline but not multiple blank lines (W292, W391)
    while lines and lines[-1] == '':
        lines.pop()

    if lines:  # Only add newline if file is not empty
        lines.append('')  # This will become the final newline

    content = '\n'.join(lines)

    # Write back if changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Main function to process all Python files."""
    if len(sys.argv) > 1:
        files_to_process = sys.argv[1:]
    else:
        # Find all Python files in current directory and subdirectories
        files_to_process = []
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.py'):
                    files_to_process.append(os.path.join(root, file))

    modified_files = []
    for file_path in files_to_process:
        if os.path.exists(file_path):
            try:
                if fix_whitespace_issues(file_path):
                    modified_files.append(file_path)
                    print(f"Fixed whitespace: {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

    if modified_files:
        print(f"\nFixed whitespace in {len(modified_files)} files")
    else:
        print("No whitespace issues found")

if __name__ == '__main__':
    main()
