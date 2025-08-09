# update_globals.py
import re
import os
import requests
from collections import defaultdict

# --- Configuration ---
# A dictionary mapping a descriptive name to its raw file URL and a parsing function.
RESOURCE_FILES = {
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
        if line.startswith('--') or not line:
            continue
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

def parse_api_definitions(content: str) -> dict:
    """
    Parses complex API files by finding all function definitions, C_TableName assignments,
    and the contents of special local tables like GlobalAPI and LuaAPI.
    """
    globals_map = defaultdict(list)
    simple_globals = set()
    string_pattern = re.compile(r"['\"]([^'\"]+)['\"]")

    # 1. Global functions: function MyFunction(...)
    for match in re.finditer(r"^\s*function\s+([A-Za-z0-9_:]+)", content, re.MULTILINE):
        simple_globals.add(match.group(1).split(':')[0])

    # 2. C_Tables and their fields: C_Table = { fields = { 'field1', ... } }
    c_table_pattern = re.compile(r"^\s*(C_[A-Za-z0-9_]+)\s*=\s*\{.*?fields\s*=\s*\{(.*?)\}", re.DOTALL | re.MULTILINE)
    for table_match in c_table_pattern.finditer(content):
        table_name = table_match.group(1)
        fields_content = table_match.group(2)
        
        for field_match in string_pattern.finditer(fields_content):
            globals_map[table_name].append(field_match.group(1))

    # 3. Strings from local API tables (GlobalAPI, LuaAPI)
    local_api_pattern = re.compile(r"^\s*local\s+(?:GlobalAPI|LuaAPI)\s*=\s*\{(.*?)\}", re.DOTALL | re.MULTILINE)
    for api_match in local_api_pattern.finditer(content):
        api_content = api_match.group(1)
        for string_match in string_pattern.finditer(api_content):
            simple_globals.add(string_match.group(1))

    # Convert simple globals to the final map format
    for s in simple_globals:
        if s not in globals_map: # Don't overwrite a complex table with a simple entry
            globals_map[s] = True
            
    return dict(globals_map)

def parse_enum_definitions(content: str) -> dict:
    """
    Parses LuaEnum files by finding all global constants (LE_*) and all
    tables assigned to a capitalized name (like Enum and Constants) and their fields.
    """
    globals_map = defaultdict(list)
    simple_globals = set()

    # 1. LE_ and NUM_LE_ constants
    for match in re.finditer(r"^\s*((?:NUM_)?LE_[A-Z0-9_]+)\s*=", content, re.MULTILINE):
        simple_globals.add(match.group(1))

    # 2. Top-level tables (Enum, Constants) and their direct children
    # This pattern captures the parent table (Enum or Constants) and the nested table definitions.
    table_block_pattern = re.compile(r"^\s*(Enum|Constants)\s*=\s*\{(.*?)\}", re.DOTALL | re.MULTILINE)
    field_pattern = re.compile(r"^\s*([A-Z][A-Za-z0-9_]+)\s*=\s*\{", re.MULTILINE)

    for block_match in table_block_pattern.finditer(content):
        parent_table = block_match.group(1)
        table_content = block_match.group(2)
        
        for field_match in field_pattern.finditer(table_content):
            globals_map[parent_table].append(field_match.group(1))

    # Convert simple globals to the final map format
    for s in simple_globals:
        globals_map[s] = True

    return dict(globals_map)

# --- Main Logic ---

def fetch_and_parse_all() -> dict:
    """Iterates through all resource files, downloads them, and applies the correct parser."""
    all_globals = defaultdict(list)
    
    parser_functions = {
        "parse_table_of_strings": parse_table_of_strings,
        "parse_global_assignments": parse_global_assignments,
        "parse_api_definitions": parse_api_definitions,
        "parse_enum_definitions": parse_enum_definitions,
    }

    # 1. Fetch globals from Blizzard's files
    for name, info in RESOURCE_FILES.items():
        url = info["url"]
        parser_func = parser_functions[info["parser"]]
        
        print(f"Downloading and parsing '{name}' from {url}...")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"::warning::Failed to download {name}: {e}")
            continue

        found_globals = parser_func(response.text)
        print(f"--> Found {len(found_globals)} globals in '{name}'.")
        
        # Merge dictionaries
        for key, value in found_globals.items():
            if value is True:
                if not isinstance(all_globals.get(key), list):
                    all_globals[key] = True
            elif isinstance(value, list):
                if all_globals[key] is True: # If it was previously simple, upgrade to list
                    all_globals[key] = []
                all_globals[key].extend(value)

    # 2. Parse custom globals from the local file
    print(f"Checking for custom globals in {CUSTOM_GLOBALS_PATH}...")
    try:
        with open(CUSTOM_GLOBALS_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        custom_globals = parse_table_of_strings(content)
        print(f"--> Found {len(custom_globals)} custom globals.")
        for key, value in custom_globals.items():
             if key not in all_globals:
                    all_globals[key] = value
    except FileNotFoundError:
        print(f"::notice::{CUSTOM_GLOBALS_PATH} not found. Creating an empty one for you.")
        with open(CUSTOM_GLOBALS_PATH, 'w', encoding='utf-8') as f:
            f.write("-- Add your own custom global variables here.\n")
            f.write("-- The script will automatically merge these with the fetched globals.\n")
            f.write('-- Use the format "MyGlobal", one per line.\n\n')

    if not all_globals:
        print("::error::No globals were extracted in total. Halting execution.")
        exit(1)

    print(f"\nSuccessfully extracted a total of {len(all_globals)} unique globals.")
    return dict(all_globals)

def update_luacheckrc(globals_dict: dict):
    """Updates the .luacheckrc file with the provided dictionary of globals."""
    print(f"Updating {LUACHECKRC_PATH}...")
    
    output_parts = []
    # Sort by global name for consistent output
    for key in sorted(globals_dict.keys()):
        value = globals_dict[key]
        
        if value is True:
            # Simple global: "MyGlobal"
            output_parts.append(f'    "{key}"')
        elif isinstance(value, list):
            # Complex global: C_Table = { fields = { ... } }
            # Deduplicate and sort fields
            sorted_fields = sorted(list(set(value)))

            complex_str = f"    {key} = {{\n"
            complex_str += "        fields = {\n"
            complex_str += ",\n".join([f"            '{field}'" for field in sorted_fields])
            complex_str += "\n        }\n    }"
            output_parts.append(complex_str)

    # Join all parts with a comma and newline
    new_globals_block_content = ",\n".join(output_parts)
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
