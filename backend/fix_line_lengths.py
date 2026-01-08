#!/usr/bin/env python3
"""
Simple script to fix line length issues by breaking long lines at logical points.
"""
import os
import re
import sys

def fix_long_lines(file_path, max_length=88):
    """Fix lines that are too long by breaking them at logical points."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified = False
    new_lines = []

    for line in lines:
        if len(line.rstrip()) > max_length:
            # Try to break at logical points
            stripped = line.rstrip()
            indent = len(line) - len(line.lstrip())
            indent_str = ' ' * indent

            # For function calls with multiple parameters
            if '(' in stripped and ')' in stripped and ',' in stripped:
                # Find the opening parenthesis
                paren_pos = stripped.find('(')
                if paren_pos > 0:
                    before_paren = stripped[:paren_pos + 1]
                    after_paren = stripped[paren_pos + 1:]

                    if len(before_paren) < max_length - 4:  # Leave room for continuation
                        # Split parameters
                        params = []
                        current_param = ""
                        paren_count = 0

                        for char in after_paren:
                            if char == '(':
                                paren_count += 1
                            elif char == ')':
                                if paren_count == 0:
                                    if current_param.strip():
                                        params.append(current_param.strip())
                                    break
                                paren_count -= 1
                            elif char == ',' and paren_count == 0:
                                if current_param.strip():
                                    params.append(current_param.strip())
                                current_param = ""
                                continue
                            current_param += char

                        if len(params) > 1:
                            new_lines.append(before_paren + '\n')
                            for i, param in enumerate(params):
                                if i == len(params) - 1:
                                    new_lines.append(indent_str + '    ' + param + ')\n')
                                else:
                                    new_lines.append(indent_str + '    ' + param + ',\n')
                            modified = True
                            continue

            # For string concatenation
            if ' + ' in stripped and '"' in stripped:
                parts = stripped.split(' + ')
                if len(parts) > 1:
                    new_lines.append(parts[0] + ' + \\\n')
                    for i, part in enumerate(parts[1:], 1):
                        if i == len(parts) - 1:
                            new_lines.append(indent_str + '    ' + part + '\n')
                        else:
                            new_lines.append(indent_str + '    ' + part + ' + \\\n')
                    modified = True
                    continue

            # For long assert statements
            if stripped.strip().startswith('assert ') and ' == ' in stripped:
                assert_parts = stripped.split(' == ', 1)
                if len(assert_parts) == 2:
                    new_lines.append(assert_parts[0] + ' == \\\n')
                    new_lines.append(indent_str + '    ' + assert_parts[1] + '\n')
                    modified = True
                    continue

        new_lines.append(line)

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
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
                if fix_long_lines(file_path):
                    modified_files.append(file_path)
                    print(f"Fixed: {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

    if modified_files:
        print(f"\nModified {len(modified_files)} files")
    else:
        print("No files needed modification")

if __name__ == '__main__':
    main()
