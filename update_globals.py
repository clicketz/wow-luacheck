# update_globals.py
import re
import os
import requests
from collections import defaultdict

# --- Configuration ---
# A dictionary mapping a descriptive name to its raw file URL and a parsing function.
RESOURCE_FILES = {
    "FrameXML": {
        "url": "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/FrameXML.lua",
        "parser": "parse_framemxml_globals"
    },
    "GlobalStrings": {
        "url": "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/GlobalStrings/enUS.lua",
        "parser": "parse_global_assignments"
    },
    "Events": {
        "url": "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/Events.lua",
        "parser": "parse_table_of_strings"
    },
    "Frames": {
        "url": "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/Frames.lua",
        "parser": "parse_table_of_strings"
    },
    "GlobalAPI": {
        "url": "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/GlobalAPI.lua",
        "parser": "parse_api_definitions"
    },
    "LuaEnum": {
        "url": "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/LuaEnum.lua",
        "parser": "parse_enum_definitions"
    },
    "Mixins": {
        "url": "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/Mixins.lua",
        "parser": "parse_table_of_strings"
    },
}

LUACHECKRC_PATH = ".luacheckrc"
CUSTOM_GLOBALS_PATH = "custom_globals.lua"

# This default content will be used if the .luacheckrc file does not exist.
DEFAULT_LUACHECKRC_CONTENT = """
std = 'lua51'
max_line_length = false
exclude_files = {'**Libs/', '**libs/'}
ignore = {
    '11./SLASH_.*', -- Setting an undefined (Slash handler) global variable
    '11./BINDING_.*', -- Setting an undefined (Keybinding header) global variable
    '113/LE_.*', -- Accessing an undefined (Lua ENUM type) global variable
    '113/NUM_LE_.*', -- Accessing an undefined (Lua ENUM type) global variable
    '211', -- Unused local variable
    '211/L', -- Unused local variable "L"
    '211/CL', -- Unused local variable "CL"
    '212', -- Unused argument
    '213', -- Unused loop variable
    '214', -- Unused hint
    -- '231', -- Set but never accessed
    '311', -- Value assigned to a local variable is unused
    '314', -- Value of a field in a table literal is unused
    '42.', -- Shadowing a local variable, an argument, a loop variable.
    '43.', -- Shadowing an upvalue, an upvalue argument, an upvalue loop variable.
    '542', -- An empty if branch
    '581', -- Error-prone operator orders
    '582', -- Error-prone operator orders
}

{globals_placeholder}
"""

# --- Parsing Strategies ---

def parse_table_of_strings(content: str) -> dict:
    """Parses files that contain a simple Lua table of strings."""
    globals_map = {}
    pattern = re.compile(r'^\s*["\']([^"\']+)["\'],?\s*$')
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('--') or not line: continue
        match = pattern.match(line)
        if match:
            globals_map[match.group(1)] = True
    return globals_map

def parse_global_assignments(content: str) -> dict:
    """Parses files that contain direct global variable assignments."""
    globals_map = {}
    pattern = re.compile(r'^([A-Z0-9_]+)\s*=')
    for line in content.splitlines():
        match = pattern.match(line)
        if match:
            globals_map[match.group(1)] = True
    return globals_map

def parse_framemxml_globals(content: str) -> dict:
    """Parses FrameXML.lua for simple functions, tables, and table methods."""
    globals_map = defaultdict(lambda: {'fields': set()})
    simple_globals = set()
    
    # Pattern for strings inside the local FrameXML and LoadOnDemand tables
    string_pattern = re.compile(r"['\"]([^'\"]+)['\"]")
    
    # Find the FrameXML and LoadOnDemand tables and extract their string contents
    table_pattern = re.compile(r"^\s*local\s+(?:FrameXML|LoadOnDemand)\s*=\s*\{(.*?)\}", re.DOTALL | re.MULTILINE)
    for table_match in table_pattern.finditer(content):
        table_content = table_match.group(1)
        for string_match in string_pattern.finditer(table_content):
            full_name = string_match.group(1)
            if "." in full_name:
                parent, field = full_name.split(".", 1)
                globals_map[parent]['fields'].add(field)
            else:
                simple_globals.add(full_name)

    for s in simple_globals:
        if s not in globals_map:
            globals_map[s] = True

    return {k: ({'fields': sorted(list(v['fields']))} if isinstance(v, dict) else v) for k, v in globals_map.items()}

def parse_api_definitions(content: str) -> dict:
    """Parses complex API files by finding C_TableName assignments and their fields."""
    globals_map = defaultdict(lambda: {'fields': set()})
    simple_globals = set()
    
    # Process C_ API tables
    c_table_pattern = re.compile(r"^\s*(C_[A-Za-z0-9_]+)\s*=\s*\{.*?fields\s*=\s*\{(.*?)\}", re.DOTALL | re.MULTILINE)
    string_pattern = re.compile(r"['\"]([^'\"]+)['\"]")
    for table_match in c_table_pattern.finditer(content):
        table_name, fields_content = table_match.groups()
        for field_match in string_pattern.finditer(fields_content):
            globals_map[table_name]['fields'].add(field_match.group(1))

    # Process simple global functions and local API tables
    for match in re.finditer(r"^\s*function\s+([A-Za-z0-9_:]+)", content, re.MULTILINE):
        simple_globals.add(match.group(1).split(':')[0])

    local_api_pattern = re.compile(r"^\s*local\s+(?:GlobalAPI|LuaAPI)\s*=\s*\{(.*?)\}", re.DOTALL | re.MULTILINE)
    for api_match in local_api_pattern.finditer(content):
        for string_match in string_pattern.finditer(api_match.group(1)):
            simple_globals.add(string_match.group(1))

    for s in simple_globals:
        if s not in globals_map:
            globals_map[s] = True

    return {k: ({'fields': sorted(list(v['fields']))} if isinstance(v, dict) else v) for k, v in globals_map.items()}

def parse_enum_definitions(content: str) -> dict:
    """Parses LuaEnum files for Enum tables and LE_ constants."""
    globals_map = defaultdict(lambda: defaultdict(lambda: {'fields': set()}))
    simple_globals = set()

    # 1. LE_ and NUM_LE_ constants
    for match in re.finditer(r"^\s*((?:NUM_)?LE_[A-Z0-9_]+)\s*=", content, re.MULTILINE):
        simple_globals.add(match.group(1))

    # 2. Top-level tables (Enum, Constants) and their direct children
    table_block_pattern = re.compile(r"^\s*(Enum|Constants)\s*=\s*\{(.*?)\}", re.DOTALL | re.MULTILINE)
    sub_table_pattern = re.compile(r"\s*([A-Z][A-Za-z0-9_]+)\s*=\s*\{(.*?)\}", re.DOTALL)
    field_pattern = re.compile(r"^\s*([A-Z][A-Za-z0-9_]+)\s*=", re.MULTILINE)

    for block_match in table_block_pattern.finditer(content):
        parent_table, table_content = block_match.groups()
        for sub_table_match in sub_table_pattern.finditer(table_content):
            sub_table_name, sub_table_content = sub_table_match.groups()
            for field_match in field_pattern.finditer(sub_table_content):
                globals_map[parent_table][sub_table_name]['fields'].add(field_match.group(1))

    for s in simple_globals:
        globals_map[s] = True

    # Convert sets to sorted lists for consistent output
    final_map = {}
    for k, v in globals_map.items():
        if isinstance(v, defaultdict):
            final_map[k] = {sub_k: {'fields': sorted(list(sub_v['fields']))} for sub_k, sub_v in v.items()}
        else:
            final_map[k] = v
    return final_map

# --- Main Logic ---

def merge_globals(d1, d2):
    """Recursively merges two dictionaries of globals."""
    for k, v in d2.items():
        if k in d1 and isinstance(d1.get(k), dict) and isinstance(v, dict):
            merge_globals(d1[k], v)
        else:
            d1[k] = v

def fetch_and_parse_all() -> dict:
    """Iterates through all resource files, downloads them, and applies the correct parser."""
    all_globals = {}
    
    parser_functions = {
        "parse_table_of_strings": parse_table_of_strings,
        "parse_global_assignments": parse_global_assignments,
        "parse_api_definitions": parse_api_definitions,
        "parse_enum_definitions": parse_enum_definitions,
        "parse_framemxml_globals": parse_framemxml_globals,
    }

    for name, info in RESOURCE_FILES.items():
        url, parser_func_name = info["url"], info["parser"]
        parser_func = parser_functions[parser_func_name]
        
        print(f"Downloading and parsing '{name}' from {url}...")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"::warning::Failed to download {name}: {e}")
            continue

        found_globals = parser_func(response.text)
        print(f"--> Found {len(found_globals)} globals in '{name}'.")
        merge_globals(all_globals, found_globals)

    print(f"Checking for custom globals in {CUSTOM_GLOBALS_PATH}...")
    try:
        with open(CUSTOM_GLOBALS_PATH, 'r', encoding='utf-8') as f:
            custom_globals = parse_table_of_strings(f.read())
        print(f"--> Found {len(custom_globals)} custom globals.")
        merge_globals(all_globals, custom_globals)
    except FileNotFoundError:
        print(f"::notice::{CUSTOM_GLOBALS_PATH} not found. Creating an empty one for you.")
        with open(CUSTOM_GLOBALS_PATH, 'w', encoding='utf-8') as f:
            f.write("-- Add your own custom global variables here.\n")

    if not all_globals:
        print("::error::No globals were extracted in total. Halting execution.")
        exit(1)

    print(f"\nSuccessfully extracted a total of {len(all_globals)} unique globals.")
    return all_globals

def format_globals_recursive(data, indent=1):
    """Recursively formats the globals dictionary into a Lua-compatible string."""
    parts = []
    indent_str = "    " * indent
    
    for key in sorted(data.keys()):
        value = data[key]
        if value is True:
            parts.append(f'{indent_str}"{key}"')
        elif isinstance(value, dict):
            sub_parts = format_globals_recursive(value, indent + 1)
            table_str = f"{indent_str}{key} = {{\n"
            table_str += ",\n".join(sub_parts)
            table_str += f"\n{indent_str}}}"
            parts.append(table_str)
        elif isinstance(value, list): # This is for 'fields' or simple lists of strings
             field_str = f"{indent_str}{key} = {{\n"
             field_str += ",\n".join([f"{indent_str}    '{f}'" for f in sorted(value)])
             field_str += f"\n{indent_str}}}"
             parts.append(field_str)
    return parts

def update_luacheckrc(globals_dict: dict):
    """Updates the .luacheckrc file with the provided dictionary of globals."""
    print(f"Updating {LUACHECKRC_PATH}...")
    
    formatted_parts = format_globals_recursive(globals_dict)
    new_globals_block_content = ",\n".join(formatted_parts)
    new_globals_block = f"globals = {{\n{new_globals_block_content}\n}}"

    if not os.path.exists(LUACHECKRC_PATH):
        print(f"{LUACHECKRC_PATH} not found. Creating a new one with default settings.")
        full_content = DEFAULT_LUACHECKRC_CONTENT.lstrip().format(globals_placeholder=new_globals_block)
        with open(LUACHECKRC_PATH, 'w', encoding='utf-8') as f:
            f.write(full_content)
        return

    with open(LUACHECKRC_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    globals_start_index = content.find("globals = {")
    if globals_start_index != -1:
        print("Found existing globals table. Replacing it and anything after.")
        base_content = content[:globals_start_index]
        new_content = base_content.rstrip() + '\n\n' + new_globals_block + '\n'
    else:
        print("No globals table found. Appending a new one.")
        new_content = content.rstrip() + '\n\n' + new_globals_block + '\n'
    
    with open(LUACHECKRC_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Update complete.")


def main():
    """Main function to run the script."""
    extracted_globals = fetch_and_parse_all()
    update_luacheckrc(extracted_globals)

if __name__ == "__main__":
    main()
