import os
import re

def fix_date_parsing():
    """Fix the date parsing issue in proj_sched.py"""
    # Path to the file
    file_path = 'src/optimization_models/proj_sched.py'
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return False
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the date parsing for week format
    # Original problematic line uses "%Y-W%W-%w" which doesn't work for day 7
    content = content.replace(
        'date = datetime.datetime.strptime(f"{year}-W{week}-7", "%Y-W%W-%w")',
        '# Convert to date using the last day of the week\n'
        '                        date = datetime.datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")\n'
        '                        # Add 6 days to get to Sunday (end of week)\n'
        '                        date = date + datetime.timedelta(days=6)'
    )
    
    # Replace any other occurrences of the problematic pattern
    pattern = r'datetime\.datetime\.strptime\(f"\{.*?\}-W\{.*?\}-(\d+)", "%Y-W%W-%w"\)'
    
    def replace_pattern(match):
        day = match.group(1)
        if day == '7':
            return 'datetime.datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w") + datetime.timedelta(days=6)'
        else:
            return f'datetime.datetime.strptime(f"{{year}}-W{{week}}-{day}", "%Y-W%W-%w")'
    
    content = re.sub(pattern, replace_pattern, content)
    
    # Write the modified content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Successfully fixed date parsing in {file_path}")
    return True

if __name__ == "__main__":
    fix_date_parsing()