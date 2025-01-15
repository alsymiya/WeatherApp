import os

"""
# Utility function to get file structure while ignoring .git files
def get_file_structure(base_dir):
    file_structure = []
    for root, dirs, files in os.walk(base_dir):
        # Ignore .git directories
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            rel_dir = os.path.relpath(root, base_dir)
            rel_file = os.path.join(rel_dir, name) if rel_dir != '.' else name
            file_structure.append(rel_file)
    return file_structure
"""

# Utility function to get file structure while ignoring .git and .pyc files
def get_file_structure(base_dir):
    file_structure = []
    for root, dirs, files in os.walk(base_dir):
        # Ignore .git directories
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            if not name.endswith('.pyc'):
                rel_dir = os.path.relpath(root, base_dir)
                rel_file = os.path.join(rel_dir, name) if rel_dir != '.' else name
                file_structure.append(rel_file)
    return file_structure

import os

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
