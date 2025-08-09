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
        "parser": "parse_function_definitions"
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
        # Ignore comments and empty lines
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

def parse_function_definitions(content: str) -> list[str]:
    """Parses files that contain global function definitions."""
    pattern = re.compile(r'^function\s+([A-Za-z0-9_:]+)\s*\(')
    globals_list = []
    for line in content.splitlines():
        match = pattern.match(line)
        if match:
            # Handle cases like 'Frame:Function()' by taking just 'Frame'
            func_name = match.group(1).split(':')[0]
            globals_list.append(func_name)
    return globals_list

def parse_enum_definitions(content: str) -> list[str]:
    """Parses files that define Lua 'enums' (tables assigned to Enum.*)."""
    pattern = re.compile(r'^(Enum\.[A-Za-z0-9_]+)\s*=')
    globals_list = []
    for line in content.splitlines():
        match = pattern.match(line)
        if match:
            globals_list.append(match.group(1))
    return globals_list

# --- Main Logic ---

def fetch_and_parse_all() -> list[str]:
    """Iterates through all resource files, downloads them, and applies the correct parser."""
    all_globals = set()
    
    parser_functions = {
        "parse_table_of_strings": parse_table_of_strings,
        "parse_global_assignments": parse_global_assignments,
        "parse_function_definitions": parse_function_definitions,
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
    
    # Format the new globals block robustly to prevent trailing commas.
    indented_globals = []
    for g in globals_list:
        # Escape any double quotes within the global name itself, just in case.
        escaped_g = g.replace('"', '\\"')
        indented_globals.append(f'    "{escaped_g}"')
    
    # Join with comma and newline. This is safer than using join with the comma inside.
    formatted_globals = ",\n".join(indented_globals)
    new_globals_block = f"globals = {{\n{formatted_globals}\n}}"

    if not os.path.exists(LUACHECKRC_PATH):
        print(f"{LUACHECKRC_PATH} not found. Creating a new one with default settings.")
        full_content = DEFAULT_LUACHECKRC_CONTENT.lstrip().format(globals_placeholder=new_globals_block)
        with open(LUACHECKRC_PATH, 'w', encoding='utf-8') as f:
            f.write(full_content)
        return

    with open(LUACHECKRC_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    globals_pattern = re.compile(r"globals\s*=\s*\{.*?\}", re.DOTALL)
    
    if globals_pattern.search(content):
        print("Found existing globals table. Replacing it.")
        new_content = globals_pattern.sub(new_globals_block, content, count=1)
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
