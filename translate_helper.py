"""Helper script for adding missing translations to locale files.

Usage: python translate_helper.py <lang_id> [--check]
Requires Python 3.9+
"""

import bisect
import io
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if sys.version_info < (3, 9):
    sys.exit("Error: This script requires Python 3.9 or later.")

# XML namespaces used by Avalonia resource dictionaries.
# XAML_NS is the default namespace; X_NS provides x:Key / x:String.
XAML_NS = 'https://github.com/avaloniaui'
X_NS = 'http://schemas.microsoft.com/winfx/2006/xaml'
STRING_TAG = f"{{{X_NS}}}String"
KEY_ATTR = f"{{{X_NS}}}Key"

# Locale file names look like "en_US", "zh_CN", "zh_Hant", etc.
LOCALE_FILE_RE = re.compile(r'([a-zA-Z]{2,3}(?:_[a-zA-Z]{2,4})*)\.axaml')


def register_namespaces() -> None:
    """Registers namespaces for ElementTree to use when writing the XML file."""
    ET.register_namespace('', XAML_NS)
    ET.register_namespace('x', X_NS)


def get_locale_dir() -> Path:
    """Constructs the absolute path for the locales files."""
    try:
        project_root = Path(__file__).resolve().parent
    except NameError:
        # __file__ may be undefined in some embedded/REPL environments
        project_root = Path.cwd()

    locales_dir = project_root / 'src' / 'Resources' / 'Locales'
    if not locales_dir.is_dir():
        print(f"Error: Locales directory not found at {locales_dir}")
        print("Please run this script from the project root.")
        sys.exit(1)

    return locales_dir


def find_reference_file(target_file: Path, locales_dir: Path) -> Path:
    """Parses the target file's ResourceInclude to locate the reference locale file."""
    try:
        root = ET.parse(target_file).getroot()
        merged_dict = root.find(f"{{{XAML_NS}}}ResourceDictionary.MergedDictionaries")
        if merged_dict is None:
            raise ValueError("Could not find MergedDictionaries tag.")

        resource_include = merged_dict.find(f"{{{XAML_NS}}}ResourceInclude")
        if resource_include is None:
            raise ValueError("Could not find ResourceInclude tag.")

        # Source is an avares:// URI; extract the locale file name from it
        include_source = resource_include.get('Source') or ''
        match = LOCALE_FILE_RE.search(include_source)
        if not match:
            raise ValueError("Could not parse reference filename from Source attribute.")

        return locales_dir / f"{match.group(1)}.axaml"
    except (ET.ParseError, ValueError, OSError) as e:
        print(f"Error parsing {target_file} to find reference file: {e}")
        sys.exit(1)


def get_locale_files(lang_id: str) -> tuple[Path, Path]:
    """Constructs the absolute paths for the target and reference locale files."""
    locales_dir = get_locale_dir()

    target_file = locales_dir / f"{lang_id}.axaml"
    if not target_file.is_file():
        print(f"Error: Target language file not found at {target_file}")
        sys.exit(1)

    ref_file = find_reference_file(target_file, locales_dir)
    if not ref_file.is_file():
        print(f"Error: Reference language file '{ref_file}' not found.")
        sys.exit(1)

    return target_file, ref_file


def get_strings(root: ET.Element) -> dict[str, str]:
    """Extracts all translation keys and their text values from an XML root."""
    strings = {}
    for string_tag in root.findall(STRING_TAG):
        key = string_tag.get(KEY_ATTR)
        if key:
            strings[key] = string_tag.text if string_tag.text is not None else ""
    return strings


def add_new_string_tag(root: ET.Element, key: str, value: str) -> None:
    """Adds a new <x:String> tag to the XML root, keeping alphabetical order."""
    new_tag = ET.Element(STRING_TAG)
    new_tag.set(KEY_ATTR, key)
    # xml:space="preserve" is required so Avalonia keeps leading/trailing
    # whitespace in translated strings
    new_tag.set("xml:space", "preserve")
    new_tag.text = value

    # Insert in alphabetical order among existing x:String elements.
    # Non-x:String children (comments, other tags) are skipped over.
    children = list(root)
    string_indices = [i for i, c in enumerate(children) if c.tag == STRING_TAG]
    keys = [(children[i].get(KEY_ATTR) or '').lower() for i in string_indices]

    if not string_indices:
        new_tag.tail = "\n  "
        root.append(new_tag)
        return

    pos = bisect.bisect_left(keys, key.lower())

    if pos >= len(string_indices):
        insert_at = string_indices[-1] + 1
    else:
        insert_at = string_indices[pos]

    # Copy the neighbouring element's tail whitespace to keep indentation consistent
    ref_index = insert_at - 1 if pos >= len(string_indices) else insert_at
    new_tag.tail = children[ref_index].tail if children[ref_index].tail else "\n  "
    root.insert(insert_at, new_tag)


def save_translations(tree: ET.ElementTree[ET.Element[str]], file_path: Path) -> None:
    """Saves the XML tree to the file, attempting to preserve formatting."""
    ET.indent(tree, space="  ")
    tree.write(file_path, encoding='utf-8', xml_declaration=False)
    print(f"\nSaved changes to {file_path}")


def ensure_utf8_stdin() -> None:
    """Forces sys.stdin to use UTF-8 decoding."""
    # sys.stdin.encoding can be None when stdin is piped or redirected
    encoding = (sys.stdin.encoding or '').lower()
    if encoding != 'utf-8':
        print("Changing input encoding to UTF-8")
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')


def main() -> None:
    """Main function to run the translation helper script."""
    if len(sys.argv) < 2:
        print("Usage: python translate_helper.py <lang_id> [--check]")
        sys.exit(1)

    ensure_utf8_stdin()

    lang_id = sys.argv[1]
    is_check_mode = len(sys.argv) > 2 and sys.argv[2] == '--check'

    register_namespaces()

    target_file_path, ref_file_path = get_locale_files(lang_id)

    # Parse files (keep comments in the target file)
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    target_tree = ET.parse(target_file_path, parser)
    target_root = target_tree.getroot()

    ref_root = ET.parse(ref_file_path).getroot()

    target_strings = get_strings(target_root)
    ref_strings = get_strings(ref_root)

    missing_keys = sorted(key for key in ref_strings if key not in target_strings)

    if not missing_keys:
        print("All keys are translated. Nothing to do.")
        return

    print(f"Found {len(missing_keys)} missing keys for language '{lang_id}'.")

    if is_check_mode:
        print("Missing keys:")
        for key in missing_keys:
            print(f"  - {key}")
        return

    print("Starting interactive translation...\n")
    changes_made = False
    try:
        for i, key in enumerate(missing_keys):
            original_text = ref_strings.get(key, "")
            print("-" * 40)
            print(f"({i+1}/{len(missing_keys)}) Key: '{key}'")
            print(f"Original: '{original_text}'")

            user_input = input("Enter translation (Enter to skip, 'q' to save and quit): ")

            if user_input.strip().lower() == 'q':
                print("\nQuitting and saving changes...")
                break
            elif user_input:
                add_new_string_tag(target_root, key, user_input)
                changes_made = True
                print(f"Added translation for '{key}'")

    except (KeyboardInterrupt, EOFError):
        print("\n\nProcess interrupted. Saving changes...")
    finally:
        if changes_made:
            save_translations(target_tree, target_file_path)
        else:
            print("\nNo changes were made.")


if __name__ == "__main__":
    main()
