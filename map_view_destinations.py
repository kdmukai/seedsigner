#!/usr/bin/env python3
"""
Script to analyze SeedSigner views and extract View classes and their Destinations.
"""

import os
import ast
import re
from typing import Dict, List, Set
from pathlib import Path

def extract_view_destinations(file_path: str) -> Dict[str, List[str]]:
    """
    Extract View class names and their Destinations from a Python file.
    
    Returns:
        Dict mapping View class names to lists of Destination class names
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {}
    
    try:
        # Parse the Python code into an Abstract Syntax Tree (AST)
        # AST represents the structure of the code as a tree of nodes
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return {}
    
    view_destinations = {}
    
    # Find all class definitions that inherit from View
    # Walk through all nodes in the AST (Abstract Syntax Tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if it's a View class (inherits from View)
            is_view = False
            if node.bases:
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == 'View':
                        is_view = True
                        break
                    elif isinstance(base, ast.Attribute) and base.attr == 'View':
                        is_view = True
                        break
            
            if is_view:
                destinations = extract_destinations_from_class(node, content)
                view_destinations[node.name] = destinations
    
    return view_destinations



def extract_destinations_from_class(class_node: ast.ClassDef, content: str) -> List[str]:
    """
    Extract Destination class names from a View class using AST parsing.
    AST (Abstract Syntax Tree) parsing analyzes the actual code structure.
    """
    destinations = set()
    
    # AST parsing for Destination() calls
    # AST parsing analyzes the actual code structure, not just text patterns
    for node in ast.walk(class_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'Destination':
                if node.args and isinstance(node.args[0], ast.Name):
                    destinations.add(node.args[0].id)
    
    return sorted(list(destinations))



def analyze_views_directory(views_dir: str) -> Dict[str, List[str]]:
    """
    Analyze all Python files in the views directory.
    
    Returns:
        Dict mapping View class names to lists of Destination class names
    """
    all_view_destinations = {}
    
    views_path = Path(views_dir)
    if not views_path.exists():
        print(f"Views directory not found: {views_dir}")
        return {}
    
    # Find all Python files in the views directory
    python_files = list(views_path.glob("*.py"))
    
    for py_file in python_files:
        if py_file.name.startswith('__'):
            continue  # Skip __init__.py and similar files
        
        print(f"Analyzing {py_file.name}...")
        file_destinations = extract_view_destinations(str(py_file))
        all_view_destinations.update(file_destinations)
    
    return all_view_destinations



def print_results(view_destinations: Dict[str, List[str]]):
    """
    Print the results in a readable format.
    """
    print("\n" + "="*60)
    print("VIEW CLASSES AND THEIR DESTINATIONS")
    print("="*60)
    
    for view_class, destinations in sorted(view_destinations.items()):
        print(f"\n{view_class}:")
        if destinations:
            for dest in destinations:
                print(f"  → {dest}")
        else:
            print("  → No destinations found")
    
    print(f"\n\nSUMMARY:")
    print(f"Total View classes found: {len(view_destinations)}")
    total_destinations = sum(len(dests) for dests in view_destinations.values())
    print(f"Total destinations found: {total_destinations}")



def export_to_dict_file(view_destinations: Dict[str, List[str]], output_file: str):
    """
    Export the results to a Python file as a dictionary.
    """
    with open(output_file, 'w') as f:
        f.write("# SeedSigner View Classes and their Destinations\n")
        f.write("# Generated automatically by analyze_views.py\n\n")
        f.write("VIEW_DESTINATIONS = {\n")
        
        for view_class, destinations in sorted(view_destinations.items()):
            dest_list = ', '.join(f'"{dest}"' for dest in destinations)
            f.write(f'    "{view_class}": [{dest_list}],\n')
        
        f.write("}\n")
    
    print(f"\nResults exported to: {output_file}")



def main():
    # Path to the SeedSigner views directory
    script_dir = Path(__file__).parent
    views_dir = script_dir / "src" / "seedsigner" / "views"
    
    if not views_dir.exists():
        print(f"Views directory not found at: {views_dir}")
        print("Please run this script from the SeedSigner root directory.")
        return
    
    print(f"Analyzing views in: {views_dir}")
    view_destinations = analyze_views_directory(str(views_dir))
    
    # Print results to console
    print_results(view_destinations)
    
    # Export to file
    output_file = script_dir / "view_destinations.py"
    export_to_dict_file(view_destinations, str(output_file))
    
    # Also print as a Python dict for direct use
    print(f"\n\nPYTHON DICT FORMAT:")
    print("VIEW_DESTINATIONS = {")
    for view_class, destinations in sorted(view_destinations.items()):
        dest_list = ', '.join(f'"{dest}"' for dest in destinations)
        print(f'    "{view_class}": [{dest_list}],')
    print("}")

if __name__ == "__main__":
    main()
