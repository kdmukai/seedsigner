#!/usr/bin/env python3
"""
Script to analyze SeedSigner views and extract View classes and their Destinations.
"""

import os
import ast
import re
from typing import Dict, List, Set, Tuple
from pathlib import Path
from collections import defaultdict, deque


def extract_settings_entries(settings_definition_path: str) -> List[Dict[str, str]]:
    """
    Extract SettingsEntry objects from settings_definition.py to include in Settings flow.
    
    Returns:
        List of dicts with 'attr_name', 'display_name', and 'view_name' for each setting
    """
    settings_entries = []
    
    try:
        with open(settings_definition_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Warning: Could not read settings_definition.py: {e}")
        return []
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Warning: Syntax error in settings_definition.py: {e}")
        return []
    
    # Look for SettingsEntry instantiations
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and 
            isinstance(node.func, ast.Name) and 
            node.func.id == 'SettingsEntry'):
            
            entry_info = {}
            
            # Extract attr_name and display_name from the SettingsEntry constructor
            for keyword in node.keywords:
                if keyword.arg == 'attr_name':
                    if isinstance(keyword.value, ast.Attribute):
                        # Handle SettingsConstants.SETTING__SOMETHING
                        if (isinstance(keyword.value.value, ast.Name) and 
                            keyword.value.value.id == 'SettingsConstants'):
                            attr_name = keyword.value.attr
                            entry_info['attr_name'] = attr_name
                            entry_info['view_name'] = f"Setting_{attr_name}"
                
                elif keyword.arg == 'display_name':
                    # Extract display name
                    display_name = None
                    if isinstance(keyword.value, ast.Call):
                        # Handle _mft("Display Name") calls
                        if (isinstance(keyword.value.func, ast.Name) and 
                            keyword.value.func.id == '_mft' and 
                            keyword.value.args):
                            if isinstance(keyword.value.args[0], ast.Constant):
                                display_name = keyword.value.args[0].value
                    elif isinstance(keyword.value, ast.Constant):
                        # Handle direct string literals
                        display_name = keyword.value.value
                    
                    if display_name:
                        entry_info['display_name'] = display_name
            
            # Only add if we have both attr_name and display_name
            if 'attr_name' in entry_info and 'display_name' in entry_info:
                settings_entries.append(entry_info)
    
    return settings_entries

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
                
                # Special handling for SettingsMenuView to include dynamic settings destinations
                if node.name == "SettingsMenuView":
                    settings_destinations = extract_settings_destinations_from_view(content)
                    view_destinations[node.name].extend(settings_destinations)
    
    return view_destinations



def extract_settings_destinations_from_view(content: str) -> List[str]:
    """
    Extract dynamic settings destinations from SettingsMenuView by analyzing how
    it processes settings_entries and creates destinations.
    
    Returns:
        List of destination view names that SettingsMenuView can navigate to
    """
    destinations = []
    
    # Look for the pattern where settings_entries are used to create destinations
    # SettingsMenuView creates destinations for:
    # 1. LocaleSelectionView (special case for SETTING__LOCALE)
    # 2. SettingsEntryUpdateSelectionView (for all other settings)
    
    # Check if this is SettingsMenuView and has settings_entries logic
    if "settings_entries" in content and "SettingsDefinition.get_settings_entries" in content:
        # Add the known destinations that SettingsMenuView creates
        destinations.extend([
            "LocaleSelectionView",  # Special case for locale setting
            "SettingsEntryUpdateSelectionView"  # General settings update view
        ])
        
        # Also look for any hardcoded settings destinations in the logic
        lines = content.split('\n')
        for line in lines:
            # Look for patterns like: return Destination(SomeView)
            if "return Destination(" in line and "View" in line:
                # Extract view name from the line
                import re
                match = re.search(r'Destination\((\w+View)', line)
                if match:
                    view_name = match.group(1)
                    if view_name not in destinations:
                        destinations.append(view_name)
    
    return destinations



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
                    dest_name = node.args[0].id
                    # Ignore BackStackView destinations as they're navigation back operations
                    if dest_name != 'BackStackView':
                        destinations.add(dest_name)
    
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
    
    # Also extract settings entries for the Settings flow
    settings_definition_path = views_path.parent / "models" / "settings_definition.py"
    if settings_definition_path.exists():
        print(f"Analyzing settings entries from {settings_definition_path.name}...")
        settings_entries = extract_settings_entries(str(settings_definition_path))
        
        # Enhance SettingsMenuView destinations to include actual settings navigation
        if "SettingsMenuView" in all_view_destinations:
            # Get existing destinations
            existing_dests = set(all_view_destinations["SettingsMenuView"])
            
            # Add the key settings destinations that SettingsMenuView actually navigates to
            settings_destinations = {
                "LocaleSelectionView",  # Special case for locale
                "SettingsEntryUpdateSelectionView",  # General settings update view
                "IOTestView",  # Hardware test
                "DonateView",  # Donate screen
            }
            
            # Add individual settings as destinations (using display names)
            for entry in settings_entries:
                settings_destinations.add(entry['display_name'])
            
            # Merge all destinations
            all_settings_dests = existing_dests.union(settings_destinations)
            all_view_destinations["SettingsMenuView"] = sorted(list(all_settings_dests))
            
            print(f"  Enhanced SettingsMenuView with {len(settings_destinations)} actual destinations")
        
        # Create entries for each individual settings entry using display names
        for entry in settings_entries:
            display_name = entry['display_name']
            attr_name = entry['attr_name']
            
            # Each settings entry navigates based on the logic in SettingsMenuView.run():
            # 1. LOCALE setting goes to LocaleSelectionView
            # 2. All other settings go to SettingsEntryUpdateSelectionView
            # 3. Both eventually return to SettingsMenuView
            
            if "LOCALE" in attr_name:
                # Special case: Locale setting has its own dedicated view
                destinations = ["LocaleSelectionView"]
            else:
                # General case: Most settings use the generic update selection view
                destinations = ["SettingsEntryUpdateSelectionView"]
            
            all_view_destinations[display_name] = destinations
        
        print(f"  Added {len(settings_entries)} individual settings entries as navigable destinations")
    
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
        f.write("# Generated automatically by map_view_destinations.py\n\n")
        f.write("VIEW_DESTINATIONS = {\n")
        
        for view_class, destinations in sorted(view_destinations.items()):
            dest_list = ', '.join(f'"{dest}"' for dest in destinations)
            f.write(f'    "{view_class}": [{dest_list}],\n')
        
        f.write("}\n")
    
    print(f"\nResults exported to: {output_file}")



def detect_cycles(view_destinations: Dict[str, List[str]]) -> List[List[str]]:
    """
    Detect circular navigation loops using DFS.
    Routes stop at MainMenuView and cross-flow boundaries to prevent false cycles.
    MainMenuView is treated as a route endpoint and excluded from cycle detection.
    
    Returns:
        List of cycles found, each cycle is a list of view names
    """
    cycles = []
    visited = set()
    rec_stack = set()
    
    # Define the four major flow entry points
    major_flow_entries = {"ScanView", "SeedsMenuView", "ToolsMenuView", "SettingsMenuView"}
    
    # Define views that should only belong to specific flows
    flow_exclusive_views = {
        "SeedOptionsView": "seeds",
    }
    
    def dfs(node: str, path: List[str], origin_flow: str = None) -> None:
        if node in rec_stack:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            cycles.append(cycle)
            return
        
        if node in visited:
            return
        
        # Stop at MainMenuView - it's a route endpoint, not part of cycles
        if node == "MainMenuView":
            visited.add(node)
            return
        
        # Stop at other major flow entry points if we didn't start from this flow
        if node in major_flow_entries and origin_flow and node != origin_flow:
            visited.add(node)
            return
        
        # Stop at flow-exclusive views that don't belong to the origin flow
        if node in flow_exclusive_views and origin_flow:
            expected_flow = flow_exclusive_views[node]
            if origin_flow != expected_flow:
                visited.add(node)
                return
        
        # Also check for conceptual settings entries
        if node.startswith("SettingsEntry_") and origin_flow and origin_flow != "settings":
            visited.add(node)
            return
        
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        # Determine origin flow if this is a flow entry point
        current_origin = origin_flow or (node if node in major_flow_entries else None)
        # For seeds flow, also recognize SeedsMenuView as the origin
        if not current_origin and node == "SeedOptionsView":
            current_origin = "seeds"
        
        # Visit all destinations
        for dest in view_destinations.get(node, []):
            if dest in view_destinations:  # Only follow if destination is also a View
                dfs(dest, path.copy(), current_origin)
        
        rec_stack.remove(node)
    
    # Start DFS from each unvisited node
    for view in view_destinations:
        if view not in visited and view != "MainMenuView":  # Skip MainMenuView entirely
            dfs(view, [])
    
    return cycles



def find_navigation_paths(view_destinations: Dict[str, List[str]], 
                         start_view: str, 
                         end_view: str,
                         max_depth: int = 10) -> List[List[str]]:
    """
    Find all navigation paths from start_view to end_view.
    Routes stop at MainMenuView and cross-flow boundaries.
    MainMenuView is treated as a route endpoint.
    
    Args:
        view_destinations: The view mapping
        start_view: Starting view name
        end_view: Target view name
        max_depth: Maximum path length to avoid infinite loops
    
    Returns:
        List of paths, each path is a list of view names
    """
    paths = []
    
    # Define the four major flow entry points
    major_flow_entries = {"ScanView", "SeedsMenuView", "ToolsMenuView", "SettingsMenuView"}
    
    # Define views that should only belong to specific flows
    flow_exclusive_views = {
        "SeedOptionsView": "seeds",
    }
    
    # Don't search for paths to/from MainMenuView - it's a route endpoint
    if start_view == "MainMenuView" or end_view == "MainMenuView":
        return paths
    
    # Determine which flows the start and end views belong to
    start_flow = start_view if start_view in major_flow_entries else None
    end_flow = end_view if end_view in major_flow_entries else None
    
    def dfs(current: str, target: str, path: List[str], visited: Set[str], origin_flow: str = None) -> None:
        if len(path) > max_depth:
            return
        
        if current == target:
            paths.append(path.copy())
            return
        
        if current in visited:
            return  # Avoid cycles
        
        # Stop at MainMenuView - it's a route endpoint
        if current == "MainMenuView":
            return
        
        # Stop at other major flow entry points unless they're our start, target, or origin
        if (current in major_flow_entries and 
            current != start_view and 
            current != end_view and
            origin_flow and 
            current != origin_flow):
            return
        
        # Stop at flow-exclusive views that don't belong to the origin flow
        if current in flow_exclusive_views and origin_flow:
            expected_flow = flow_exclusive_views[current]
            if origin_flow != expected_flow and current != start_view and current != end_view:
                return
        
        # Also check for conceptual settings entries
        if current.startswith("SettingsEntry_") and origin_flow and origin_flow != "settings" and current != start_view and current != end_view:
            return
        
        visited.add(current)
        
        # Update origin flow if we're at a flow entry point
        current_origin = origin_flow or (current if current in major_flow_entries else None)
        # For seeds flow, also recognize when we're in seeds-exclusive views
        if not current_origin and current == "SeedOptionsView":
            current_origin = "seeds"
        
        for dest in view_destinations.get(current, []):
            if dest in view_destinations:  # Only follow if destination is also a View
                path.append(dest)
                dfs(dest, target, path, visited.copy(), current_origin)
                path.pop()
    
    if start_view in view_destinations:
        dfs(start_view, end_view, [start_view], set(), start_flow)
    
    return paths



def export_to_graphviz(view_destinations: Dict[str, List[str]], output_file: str):
    """
    Export the view mapping to Graphviz DOT format for visualization.
    """
    with open(output_file, 'w') as f:
        f.write("digraph SeedSignerViews {\n")
        f.write("    rankdir=TB;\n")
        f.write("    node [shape=box, style=rounded];\n")
        f.write("    edge [color=blue];\n\n")
        
        # Add all nodes
        for view in view_destinations:
            f.write(f'    "{view}" [label="{view}"];\n')
        
        f.write("\n")
        
        # Add edges
        for view, destinations in view_destinations.items():
            for dest in destinations:
                f.write(f'    "{view}" -> "{dest}";\n')
        
        f.write("}\n")
    
    print(f"Graphviz DOT file exported to: {output_file}")
    print("To generate PNG: dot -Tpng {0} -o {0}.png".format(output_file))
    print("To generate SVG: dot -Tsvg {0} -o {0}.svg".format(output_file))



def export_to_mermaid(view_destinations: Dict[str, List[str]], output_file: str):
    """
    Export the view mapping to Mermaid diagram format.
    """
    with open(output_file, 'w') as f:
        f.write("```mermaid\n")
        f.write("graph TD\n")
        
        # Add edges (nodes are implicit)
        for view, destinations in view_destinations.items():
            for dest in destinations:
                # Clean view names for Mermaid (replace special characters)
                clean_view = view.replace(" ", "_").replace("-", "_")
                clean_dest = dest.replace(" ", "_").replace("-", "_")
                f.write(f"    {clean_view}[\"{view}\"] --> {clean_dest}[\"{dest}\"]\n")
        
        f.write("```\n")
    
    print(f"Mermaid diagram exported to: {output_file}")



def analyze_navigation_structure(view_destinations: Dict[str, List[str]]):
    """
    Analyze the navigation structure and provide insights.
    """
    print("\n" + "="*60)
    print("NAVIGATION STRUCTURE ANALYSIS")
    print("="*60)
    
    # Calculate statistics
    total_views = len(view_destinations)
    total_connections = sum(len(dests) for dests in view_destinations.values())
    
    # Find entry points (views with no incoming connections)
    all_destinations = set()
    for dests in view_destinations.values():
        all_destinations.update(dests)
    
    entry_points = []
    for view in view_destinations:
        if view not in all_destinations:
            entry_points.append(view)
    
    # Find dead ends (views with no outgoing connections)
    dead_ends = [view for view, dests in view_destinations.items() if not dests]
    
    # Find most connected views
    outgoing_counts = [(view, len(dests)) for view, dests in view_destinations.items()]
    outgoing_counts.sort(key=lambda x: x[1], reverse=True)
    
    incoming_counts = defaultdict(int)
    for dests in view_destinations.values():
        for dest in dests:
            incoming_counts[dest] += 1
    incoming_sorted = sorted(incoming_counts.items(), key=lambda x: x[1], reverse=True)
    
    print(f"Total Views: {total_views}")
    print(f"Total Connections: {total_connections}")
    print(f"Average connections per view: {total_connections/total_views:.2f}")
    
    print(f"\nEntry Points ({len(entry_points)}):")
    for ep in entry_points[:10]:  # Show top 10
        print(f"  • {ep}")
    if len(entry_points) > 10:
        print(f"  ... and {len(entry_points) - 10} more")
    
    print(f"\nDead Ends ({len(dead_ends)}):")
    for de in dead_ends[:10]:  # Show top 10
        print(f"  • {de}")
    if len(dead_ends) > 10:
        print(f"  ... and {len(dead_ends) - 10} more")
    
    print(f"\nMost Outgoing Connections:")
    for view, count in outgoing_counts[:5]:
        print(f"  • {view}: {count} destinations")
    
    print(f"\nMost Incoming Connections:")
    for view, count in incoming_sorted[:5]:
        print(f"  • {view}: {count} sources")
    
    # Detect cycles
    cycles = detect_cycles(view_destinations)
    print(f"\nCircular Navigation Loops Found: {len(cycles)}")
    for i, cycle in enumerate(cycles[:5]):  # Show first 5 cycles
        print(f"  • Cycle {i+1}: {' → '.join(cycle)}")
    if len(cycles) > 5:
        print(f"  ... and {len(cycles) - 5} more cycles")



def extract_flow_subgraph(view_destinations: Dict[str, List[str]], 
                         start_view: str, 
                         max_depth: int = 15) -> Dict[str, List[str]]:
    """
    Extract a subgraph starting from a specific view, following all reachable paths.
    Routes stop at MainMenuView and other major flow entry points to prevent cross-flow contamination.
    MainMenuView is treated as a route endpoint and excluded from results.
    
    Args:
        view_destinations: Complete view mapping
        start_view: Starting view for the flow
        max_depth: Maximum depth to prevent infinite loops
    
    Returns:
        Filtered view mapping containing only views reachable from start_view
    """
    if start_view not in view_destinations:
        return {}
    
    # Define the four major flow entry points and important sub-flow boundaries
    major_flow_entries = {
        "ScanView": "scan",
        "SeedsMenuView": "seeds", 
        "ToolsMenuView": "tools",
        "SettingsMenuView": "settings"
    }
    
    # Define views that should only belong to specific flows
    flow_exclusive_views = {
        "SeedOptionsView": "seeds",
        # Settings entries are also exclusive to settings flow - using dynamic generation
    }
    # Add settings entries dynamically
    settings_attrs = [
        "SETTING__LOCALE", "SETTING__WORDLIST_LANGUAGE", "SETTING__PERSISTENT_SETTINGS",
        "SETTING__COORDINATORS", "SETTING__BTC_DENOMINATION", "SETTING__NETWORK", 
        "SETTING__QR_DENSITY", "SETTING__XPUB_EXPORT", "SETTING__SIG_TYPES",
        "SETTING__SCRIPT_TYPES", "SETTING__XPUB_DETAILS", "SETTING__PASSPHRASE",
        "SETTING__BIP85_CHILD_SEEDS", "SETTING__SEEDQR_FORMAT", "SETTING__QR_BRIGHTNESS",
        "SETTING__CAMERA_ROTATION", "SETTING__MESSAGE_SIGNING", "SETTING__PAYJOIN",
        "SETTING__PRIVACY_WARNINGS", "SETTING__DIRE_WARNINGS", "SETTING__PARTNER_LOGOS",
        "SETTING__COMPACT_SEEDQR"
    ]
    for attr in settings_attrs:
        flow_exclusive_views[f"Setting_{attr}_View"] = "settings"
    
    # Determine which flow we're analyzing
    current_flow = major_flow_entries.get(start_view, "unknown")
    
    reachable_views = set()
    
    def dfs(current: str, depth: int) -> None:
        if depth > max_depth or current in reachable_views:
            return
        
        # Never include MainMenuView in results - it's a route endpoint
        if current == "MainMenuView":
            return
        
        # Stop at other major flow entry points (cross-flow boundary)
        # Don't continue into other flows, but do add them to show the boundary
        if current in major_flow_entries and current != start_view:
            return  # Don't continue into other flows AND don't add them
        
        # Stop at flow-exclusive views that don't belong to this flow
        if current in flow_exclusive_views:
            expected_flow = flow_exclusive_views[current]
            if current_flow != expected_flow:
                return  # Don't include views from other flows
        
        # Also check for settings entries by looking at their destination patterns
        if current_flow != "settings":
            current_destinations = view_destinations.get(current, [])
            # If a view only routes to SettingsEntryUpdateSelectionView or LocaleSelectionView,
            # it's likely a settings entry and should be settings-exclusive
            if (len(current_destinations) <= 2 and 
                any(dest in ["SettingsEntryUpdateSelectionView", "LocaleSelectionView"] 
                    for dest in current_destinations) and
                not current.endswith("View")):  # Don't apply to actual View classes
                return  # Don't include settings entries in non-settings flows
        
        reachable_views.add(current)
        
        for dest in view_destinations.get(current, []):
            if dest in view_destinations:  # Only follow if destination is also a View
                dfs(dest, depth + 1)
    
    dfs(start_view, 0)
    
    # Build filtered mapping
    flow_mapping = {}
    for view in reachable_views:
        if view in view_destinations:
            # Filter destinations: exclude MainMenuView, cross-flow boundaries, and unreachable views
            filtered_dests = []
            for dest in view_destinations[view]:
                if dest in reachable_views:
                    # Only include if it's in our reachable set
                    filtered_dests.append(dest)
                elif dest == 'BackStackView':
                    # Always include BackStackView
                    filtered_dests.append(dest)
                # Exclude MainMenuView and cross-flow boundaries entirely
            
            flow_mapping[view] = filtered_dests
    
    return flow_mapping



def export_flow_visualizations(view_destinations: Dict[str, List[str]], script_dir: Path):
    """
    Export separate visualization files for each main menu flow.
    """
    # Define the four main flows from MainMenuView
    main_flows = {
        "scan": {
            "start_view": "ScanView",
            "title": "Scan Flow",
            "description": "QR code scanning and transaction workflows"
        },
        "seeds": {
            "start_view": "SeedsMenuView", 
            "title": "Seeds Flow",
            "description": "Seed phrase generation, import, and management"
        },
        "tools": {
            "start_view": "ToolsMenuView",
            "title": "Tools Flow", 
            "description": "Utility tools and advanced features"
        },
        "settings": {
            "start_view": "SettingsMenuView",
            "title": "Settings Flow",
            "description": "Configuration and preferences"
        }
    }
    
    print(f"\n\nCREATING SEPARATE FLOW VISUALIZATIONS:")
    print("="*50)
    
    for flow_name, flow_info in main_flows.items():
        start_view = flow_info["start_view"]
        title = flow_info["title"]
        description = flow_info["description"]
        
        # Extract subgraph for this flow
        flow_mapping = extract_flow_subgraph(view_destinations, start_view)
        
        if not flow_mapping:
            print(f"⚠️  {title}: No views found starting from {start_view}")
            continue
        
        print(f"📊 {title}: {len(flow_mapping)} views, {sum(len(dests) for dests in flow_mapping.values())} connections")
        print(f"   {description}")
        
        # Show cross-flow connections that were stopped
        cross_flow_connections = []
        main_menu_connections = []
        for view in flow_mapping:
            if view in view_destinations:
                for dest in view_destinations[view]:
                    if dest in {"ScanView", "SeedsMenuView", "ToolsMenuView", "SettingsMenuView"} and dest != start_view:
                        cross_flow_connections.append(f"{view} → {dest}")
                    elif dest == "MainMenuView":
                        main_menu_connections.append(f"{view} → MainMenu")
                    elif dest in {"SeedOptionsView"} and start_view not in {"SeedsMenuView"}:
                        cross_flow_connections.append(f"{view} → {dest} (seeds-only)")
                    elif dest.startswith("Setting_") and dest.endswith("_View") and start_view not in {"SettingsMenuView"}:
                        cross_flow_connections.append(f"{view} → {dest} (settings-only)")
                    elif dest.startswith("SettingsEntry_") and start_view not in {"SettingsMenuView"}:
                        cross_flow_connections.append(f"{view} → {dest} (settings-only)")
        
        if cross_flow_connections:
            print(f"   Cross-flow connections stopped: {len(cross_flow_connections)}")
            for conn in cross_flow_connections[:3]:  # Show first 3
                print(f"     • {conn}")
            if len(cross_flow_connections) > 3:
                print(f"     ... and {len(cross_flow_connections) - 3} more")
        
        if main_menu_connections:
            print(f"   Return-to-main-menu routes: {len(main_menu_connections)}")
            for conn in main_menu_connections[:3]:  # Show first 3
                print(f"     • {conn}")
            if len(main_menu_connections) > 3:
                print(f"     ... and {len(main_menu_connections) - 3} more")
        
        # Export Graphviz for this flow
        dot_file = script_dir / f"view_navigation_{flow_name}.dot"
        with open(dot_file, 'w') as f:
            f.write(f"digraph SeedSigner_{title.replace(' ', '_')} {{\n")
            f.write(f"    label=\"{title} - {description}\";\n")
            f.write("    labelloc=t;\n")
            f.write("    rankdir=TB;\n")
            f.write("    node [shape=box, style=rounded];\n")
            f.write("    edge [color=blue];\n\n")
            
            # Highlight the start view
            f.write(f'    "{start_view}" [style="rounded,filled", fillcolor=lightgreen, label="{start_view}\\n(Entry Point)"];\n')
            
            # Add other nodes
            for view in flow_mapping:
                if view != start_view:
                    f.write(f'    "{view}" [label="{view}"];\n')
            
            f.write("\n")
            
            # Add edges
            for view, destinations in flow_mapping.items():
                for dest in destinations:
                    if dest != 'BackStackView':  # Skip back navigation for clarity
                        f.write(f'    "{view}" -> "{dest}";\n')
            
            f.write("}\n")
        
        # Export Mermaid for this flow
        md_file = script_dir / f"view_navigation_{flow_name}.md"
        with open(md_file, 'w') as f:
            f.write(f"# {title}\n\n")
            f.write(f"{description}\n\n")
            f.write("```mermaid\n")
            f.write("graph TD\n")
            f.write(f"    Start([START: {start_view}])\n")
            f.write(f"    Start --> {start_view.replace(' ', '_')}\n")
            
            # Add edges (nodes are implicit)
            for view, destinations in flow_mapping.items():
                for dest in destinations:
                    if dest != 'BackStackView':  # Skip back navigation
                        clean_view = view.replace(" ", "_").replace("-", "_")
                        clean_dest = dest.replace(" ", "_").replace("-", "_")
                        f.write(f"    {clean_view}[\"{view}\"] --> {clean_dest}[\"{dest}\"]\n")
            
            f.write("```\n")
        
        print(f"   • {dot_file.name}")
        print(f"   • {md_file.name}")
    
    # Also create a combined overview
    overview_dot = script_dir / "view_navigation_overview.dot"
    with open(overview_dot, 'w') as f:
        f.write("digraph SeedSignerOverview {\n")
        f.write("    label=\"SeedSigner Navigation Overview\";\n")
        f.write("    labelloc=t;\n")
        f.write("    rankdir=TB;\n")
        f.write("    node [shape=box, style=rounded];\n")
        f.write("    edge [color=blue];\n\n")
        
        # Create clusters for each main flow
        for i, (flow_name, flow_info) in enumerate(main_flows.items()):
            start_view = flow_info["start_view"]
            title = flow_info["title"]
            flow_mapping = extract_flow_subgraph(view_destinations, start_view)
            
            if flow_mapping:
                f.write(f"    subgraph cluster_{i} {{\n")
                f.write(f"        label=\"{title}\";\n")
                f.write("        style=filled;\n")
                f.write(f"        color=lightgrey;\n")
                
                # Add nodes in this cluster
                for view in list(flow_mapping.keys())[:8]:  # Limit to prevent overcrowding
                    f.write(f"        \"{view}\";\n")
                
                f.write("    }\n\n")
        
        # Add MainMenuView at the top
        f.write('    "MainMenuView" [style="rounded,filled", fillcolor=yellow, label="MainMenuView\\n(Main Hub)"];\n')
        
        # Connect MainMenuView to each flow start
        for flow_name, flow_info in main_flows.items():
            start_view = flow_info["start_view"]
            if start_view in view_destinations:
                f.write(f'    "MainMenuView" -> "{start_view}";\n')
        
        f.write("}\n")
    
    print(f"\n📈 Overview diagram: {overview_dot.name}")
    
    return main_flows

def main():
    # Path to the SeedSigner views directory
    script_dir = Path(__file__).parent.parent  # Go up one level from tools/ to project root
    views_dir = script_dir / "src" / "seedsigner" / "views"
    
    if not views_dir.exists():
        print(f"Views directory not found at: {views_dir}")
        print("Please run this script from the SeedSigner root directory or tools/ subdirectory.")
        return
    
    print(f"Analyzing views in: {views_dir}")
    view_destinations = analyze_views_directory(str(views_dir))
    
    # Print results to console
    print_results(view_destinations)
    
    # Analyze navigation structure
    analyze_navigation_structure(view_destinations)
    
    # Export separate flow visualizations for each main menu option
    main_flows = export_flow_visualizations(view_destinations, script_dir)
    
    # Export combined data file
    output_file = script_dir / "view_destinations.py"
    export_to_dict_file(view_destinations, str(output_file))
    
    # Example: Find paths between specific views
    print(f"\n\nEXAMPLE NAVIGATION PATHS:")
    print("="*40)
    
    # Find some example paths within each flow
    example_paths = []
    for flow_name, flow_info in main_flows.items():
        start_view = flow_info["start_view"]
        if start_view in view_destinations:
            # Find a few destination views in this flow to show example paths
            flow_mapping = extract_flow_subgraph(view_destinations, start_view)
            potential_targets = [v for v in flow_mapping.keys() if v != start_view][:2]
            
            for target in potential_targets:
                example_paths.append((start_view, target, flow_info["title"]))
    
    for start, end, flow_title in example_paths:
        paths = find_navigation_paths(view_destinations, start, end, max_depth=6)
        print(f"\n{flow_title} - {start} to {end}:")
        if paths:
            for i, path in enumerate(paths[:2]):  # Show first 2 paths
                print(f"  Path {i+1}: {' → '.join(path)}")
            if len(paths) > 2:
                print(f"  ... and {len(paths) - 2} more paths")
        else:
            print(f"  No direct paths found")
    
    # Also print as a Python dict for direct use
    print(f"\n\nPYTHON DICT FORMAT:")
    print("VIEW_DESTINATIONS = {")
    for view_class, destinations in sorted(view_destinations.items()):
        dest_list = ', '.join(f'"{dest}"' for dest in destinations)
        print(f'    "{view_class}": [{dest_list}],')
    print("}")
    
    print(f"\n\n🎯 VISUALIZATION FILES CREATED:")
    print("="*50)
    print(f"\n📊 Main Menu Flow Diagrams:")
    for flow_name, flow_info in main_flows.items():
        print(f"  • {flow_info['title']}:")
        print(f"    - view_navigation_{flow_name}.dot")
        print(f"    - view_navigation_{flow_name}.md")
    
    print(f"\n📈 Combined Files:")
    print(f"  • view_navigation_overview.dot (All flows overview)")
    print(f"  • view_destinations.py (Python data)")
    
    print(f"\n🚀 To Visualize:")
    print(f"1. Install Graphviz: brew install graphviz")
    print(f"2. Generate images:")
    for flow_name in main_flows.keys():
        print(f"   dot -Tpng view_navigation_{flow_name}.dot -o view_navigation_{flow_name}.png")
    print(f"   dot -Tpng view_navigation_overview.dot -o view_navigation_overview.png")
    print(f"3. View Mermaid online: https://mermaid.live/")
    
    print(f"\n💡 Usage Tips:")
    print(f"  • Each flow shows views reachable from that main menu option")
    print(f"  • BackStackView destinations are filtered out for clarity")
    print(f"  • Overview diagram shows high-level flow relationships")
    print(f"  • Use individual flow diagrams for detailed analysis")

if __name__ == "__main__":
    main()
