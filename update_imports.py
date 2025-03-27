#!/usr/bin/env python3
"""
Script to update import statements in worker files to use app prefix.
"""

import os
import sys
import re

def update_imports_in_file(file_path):
    """Update import statements in a file to use app prefix."""
    print(f"Processing {file_path}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update from workers.X import Y
    updated_content = re.sub(
        r'from workers\.(.*) import (.*)',
        r'from app.workers.\1 import \2',
        content
    )
    
    # Update from models.X import Y
    updated_content = re.sub(
        r'from models\.(.*) import (.*)',
        r'from app.models.\1 import \2',
        updated_content
    )
    
    # Update import workers.X
    updated_content = re.sub(
        r'import workers\.(.*)',
        r'import app.workers.\1',
        updated_content
    )
    
    # Update import models.X
    updated_content = re.sub(
        r'import models\.(.*)',
        r'import app.models.\1',
        updated_content
    )
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(updated_content)

def process_directory(directory):
    """Process all Python files in a directory and its subdirectories."""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                update_imports_in_file(file_path)

if __name__ == "__main__":
    # Process app/workers directory
    worker_dir = os.path.join('app', 'workers')
    process_directory(worker_dir)
    print("Done updating imports in worker files.")
    
    # Process app/routers directory
    router_dir = os.path.join('app', 'routers')
    process_directory(router_dir)
    print("Done updating imports in router files.")
    
    # Process app/game_state directory
    game_state_dir = os.path.join('app', 'game_state')
    process_directory(game_state_dir)
    print("Done updating imports in game_state files.")
    
    # Process app/ai directory
    ai_dir = os.path.join('app', 'ai')
    process_directory(ai_dir)
    print("Done updating imports in ai files.")