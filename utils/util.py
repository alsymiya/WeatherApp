import os
import json
from datetime import datetime

# Utility function to get file structure while ignoring .gitattributes, .git and .pyc files
def get_file_structure(base_dir):
    file_structure = []
    for root, dirs, files in os.walk(base_dir):
        # Ignore .git directories
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            if not name.endswith('.pyc') and not name.endswith('.gitattributes'):
                rel_dir = os.path.relpath(root, base_dir)
                rel_file = os.path.join(rel_dir, name) if rel_dir != '.' else name
                file_structure.append(rel_file)
    return file_structure


def format_file_structure(file_structure):
    """
    Formats a list of file paths into a tree-like structure.
    Args:
        file_structure (list): List of file paths.
    Returns:
        str: Formatted string representing the tree structure.
    """
    tree = {}
    for path in file_structure:
        parts = path.replace("\\", "/").split("/")  # Normalize paths for cross-platform compatibility
        current = tree
        for part in parts:
            current = current.setdefault(part, {})  # Build nested dictionary
    return build_tree_string(tree)


def build_tree_string(tree, prefix=""):
    """
    Recursively builds a tree-like string representation.
    Args:
        tree (dict): Nested dictionary representing the tree.
        prefix (str): Prefix for the current level.
    Returns:
        str: Tree structure as a string.
    """
    lines = []
    items = list(tree.items())  # Extract key-value pairs for iteration]
    
    for i, (key, subtree) in enumerate(items):
        connector = "├── " if i < len(items) - 1 else "└── "
        lines.append(f"{prefix}{connector}{key}")
        if subtree:  # If the current node has children
            extension = "│   " if i < len(items) - 1 else "    "
            subtree_lines = build_tree_string(subtree, prefix + extension).split("\n")
            lines.extend(subtree_lines)
    return "\n".join(lines)


def format_weather_data(weather_data):
    try:
        # Parse the string into a dictionary
        data = json.loads(weather_data)
        formatted_data = {
            "Location": data.get("name", "Unknown"),
            "Temperature": f"{data['main']['temp']} °C",
            "Feels Like": f"{data['main']['feels_like']} °C",
            "Weather": data['weather'][0]['description'].capitalize(),
            "Wind Speed": f"{data['wind']['speed']} m/s",
            "Pressure": f"{data['main']['pressure']} hPa",
            "Humidity": f"{data['main']['humidity']}%",
            "Sunrise": datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M:%S'),
            "Sunset": datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M:%S'),
        }
        return formatted_data
    except Exception as e:
        return {"Error": str(e)}
    

