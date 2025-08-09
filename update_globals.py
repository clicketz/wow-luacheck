# update_globals.py
import re
import os
import requests

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
        "parser": "parse_api_definitions" # Using a more specific parser for this complex file
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

def parse_table_of_strings(content: str) -> list[str]:
    """Parses files that contain a simple Lua table of strings."""
    pattern = re.compile(r'^\s*"([^"]+)",?\s*$')
    globals_list = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('--') or not line:
            continue
        match = pattern.match(line)
        if match:
            globals_list.append(match.group(1))
    return globals_list

def parse_global_assignments(content: str) -> list[str]:
    """Parses files that contain direct global variable assignments."""
    pattern = re.compile(r'^([A-Z0-9_]+)\s*=')
    globals_list = []
    for line in content.splitlines():
        match = pattern.match(line)
        if match:
            globals_list.append(match.group(1))
    return globals_list

def parse_api_definitions(content: str) -> list[str]:
    """
    Parses complex API files by finding all function definitions, C_TableName assignments,
    and the contents of special local tables like GlobalAPI and LuaAPI.
    """
    globals_list = set()
    string_pattern = re.compile(r"['\"]([^'\"]+)['\"]")

    # 1. Global functions: function MyFunction(...)
    for match in re.finditer(r"^\s*function\s+([A-Za-z0-9_:]+)", content, re.MULTILINE):
        globals_list.add(match.group(1).split(':')[0])

    # 2. C_Tables and their fields: C_Table = { fields = { 'field1', ... } }
    # This pattern captures the C_Table name and the entire content of its 'fields' sub-table.
    c_table_pattern = re.compile(r"^\s*(C_[A-Za-z0-9_]+)\s*=\s*\{.*?fields\s*=\s*\{(.*?)\}", re.DOTALL | re.MULTILINE)
    for table_match in c_table_pattern.finditer(content):
        table_name = table_match.group(1)
        fields_content = table_match.group(2)
        globals_list.add(table_name)
        for field_match in string_pattern.finditer(fields_content):
            globals_list.add(field_match.group(1))

    # 3. Strings from local API tables (GlobalAPI, LuaAPI)
    local_api_pattern = re.compile(r"^\s*local\s+(?:GlobalAPI|LuaAPI)\s*=\s*\{(.*?)\}", re.DOTALL | re.MULTILINE)
    for api_match in local_api_pattern.finditer(content):
        api_content = api_match.group(1)
        for string_match in string_pattern.finditer(api_content):
            globals_list.add(string_match.group(1))
            
    return list(globals_list)

def parse_enum_definitions(content: str) -> list[str]:
    """
    Parses LuaEnum files by finding all global constants (LE_*) and all
    tables assigned to a capitalized name (like Enum and Constants).
    """
    globals_list = set()

    # 1. LE_ and NUM_LE_ constants
    for match in re.finditer(r"^\s*((?:NUM_)?LE_[A-Z0-9_]+)\s*=", content, re.MULTILINE):
        globals_list.add(match.group(1))

    # 2. Top-level tables (Enum, Constants) and their direct children
    # This finds all capitalized words that are assigned a table.
    # This will capture Enum, Constants, and all the tables nested one level deep inside them.
    for match in re.finditer(r"^\s*([A-Z][A-Za-z0-9_]+)\s*=\s*\{", content, re.MULTILINE):
        globals_list.add(match.group(1))

    return list(globals_list)

# --- Main Logic ---

def fetch_and_parse_all() -> list[str]:
    """Iterates through all resource files, downloads them, and applies the correct parser."""
    all_globals = set()
    
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
        all_globals.update(found_globals)

    # 2. Parse custom globals from the local file
    print(f"Checking for custom globals in {CUSTOM_GLOBALS_PATH}...")
    try:
        with open(CUSTOM_GLOBALS_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        custom_globals = parse_table_of_strings(content)
        print(f"--> Found {len(custom_globals)} custom globals.")
        all_globals.update(custom_globals)
    except FileNotFoundError:
        print(f"::notice::{CUSTOM_GLOBALS_PATH} not found. Creating an empty one for you.")
        with open(CUSTOM_GLOBALS_PATH, 'w', encoding='utf-8') as f:
            f.write("-- Add your own custom global variables here.\n")
            f.write("-- The script will automatically merge these with the fetched globals.\n")
            f.write('-- Use the format "MyGlobal", one per line.\n\n')

    if not all_globals:
        print("::error::No globals were extracted in total. Halting execution.")
        exit(1)

    sorted_globals = sorted(list(all_globals))
    print(f"\nSuccessfully extracted a total of {len(sorted_globals)} unique globals.")
    return sorted_globals

def update_luacheckrc(globals_list: list[str]):
    """Updates the .luacheckrc file with the provided list of globals."""
    print(f"Updating {LUACHECKRC_PATH}...")
    
    # Format the new globals block
    indented_globals = []
    for g in globals_list:
        escaped_g = g.replace('"', '\\"')
        indented_globals.append(f'    "{escaped_g}"')
    
    formatted_globals = ",\n".join(indented_globals)
    new_globals_block = f"globals = {{\n{formatted_globals}\n}}"

    # If .luacheckrc doesn't exist, create it with the default template.
    if not os.path.exists(LUACHECKRC_PATH):
        print(f"{LUACHECKRC_PATH} not found. Creating a new one with default settings.")
        full_content = DEFAULT_LUACHECKRC_CONTENT.lstrip().format(globals_placeholder=new_globals_block)
        with open(LUACHECKRC_PATH, 'w', encoding='utf-8') as f:
            f.write(full_content)
        return

    # If the file exists, read its content and replace or append the globals block.
    with open(LUACHECKRC_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the start of the globals block to truncate from there.
    globals_start_index = content.find("globals = {")

    if globals_start_index != -1:
        # Keep everything before the globals block and discard the rest.
        print("Found existing globals table. Replacing it and anything after.")
        base_content = content[:globals_start_index]
        new_content = base_content.rstrip() + '\n\n' + new_globals_block + '\n'
    else:
        # No globals block found, just append to the end.
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
