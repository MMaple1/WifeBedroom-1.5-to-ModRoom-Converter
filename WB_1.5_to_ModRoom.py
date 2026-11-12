#!/usr/bin/env python3
"""
WB 1.5 to ModRoom Converter v1.0
-------------------------------------------------------------------------------
Converts Wife's Bedroom v1.5 custom mods, Steam Workshop numeric folders,
and unified custom/ directories into ModRoom's category architecture:
  - custom_futas/    (Lovers)
  - custom_wives/    (Partners / Spouses)
  - custom_bedrooms/ (Room Backgrounds)

Features:
  - Workshop Name Resolver: Parses internal INI data to turn numeric IDs
    (e.g. 3821177370) into clean, human-readable character names (e.g. ankha).
  - Safe Collision Disambiguation: Appends ID tags if duplicate names are detected.
  - File Filter: Strips raw art project files (.aseprite, .clip, .pdn, .kra, .zip)
    and backup files (.bak, ~) for clean, lightweight game-ready packs.
  - Manifest Generation: Generates clean _manifest.txt files for mobile & PC compatibility.
  - Destination Selection: Export to output/ModRoom_Mods/ or merge directly
    into an existing ModRoom installation.
-------------------------------------------------------------------------------
"""

import sys
import os
import re
import shutil
import zipfile
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set

VALID_EXTENSIONS = {
    ".png", ".ogg", ".wav", ".mp3", ".json",
    ".futa", ".spouse", ".wife", ".bedroom",
    ".ini", ".txt", ".jpg", ".jpeg", ".gif", ".webp"
}

IGNORED_PROJECT_EXTENSIONS = {
    ".aseprite", ".ase", ".clip", ".pdn", ".kra",
    ".psd", ".xcf", ".blend", ".zip", ".rar", ".7z",
    ".bak", ".tmp"
}

def sanitize_name(name: str) -> str:
    """Sanitizes names into clean, lowercase filesystem and manifest-safe identifiers."""
    clean = re.sub(r'[\/:*?"<>|]', "_", str(name)).strip()
    clean = clean.lower()
    clean = re.sub(r'\s+', '_', clean)
    clean = re.sub(r'_+', '_', clean).strip('_')
    return clean or "unnamed_mod"

def extract_pack_display_name(pack_path: Path) -> str:
    """
    Inspects .futa, .spouse, or .bedroom INI files inside a pack to extract
    the real character name from [info] name=, converting numeric Workshop IDs
    into clean display names (e.g., 3821177370 -> Ankha).
    """
    for data_file in pack_path.glob("custom_data.*"):
        if data_file.is_file() and data_file.suffix.lower() in [".futa", ".spouse", ".wife", ".bedroom"]:
            try:
                content = data_file.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r"^\s*name\s*=\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
                if m:
                    extracted = m.group(1).strip()
                    extracted = re.sub(r'[\/:*?"<>|]', "", extracted).strip()
                    if extracted and len(extracted) >= 2:
                        return extracted
            except Exception:
                pass

    for ini_file in pack_path.glob("*.ini"):
        if ini_file.is_file():
            try:
                content = ini_file.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r"^\s*name\s*=\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
                if m:
                    extracted = m.group(1).strip()
                    extracted = re.sub(r'[\/:*?"<>|]', "", extracted).strip()
                    if extracted and len(extracted) >= 2:
                        return extracted
            except Exception:
                pass

    return pack_path.name

def detect_pack_category(pack_path: Path) -> Optional[str]:
    """
    Identifies whether a v1.5 mod pack is a Lover (Futa), Partner (Wife),
    or Bedroom based on header data files.
    """
    if (pack_path / "custom_data.futa").exists():
        return "custom_futas"
    if (pack_path / "custom_data.spouse").exists() or (pack_path / "custom_data.wife").exists():
        return "custom_wives"
    if (pack_path / "custom_data.bedroom").exists():
        return "custom_bedrooms"

    for f in pack_path.iterdir():
        if f.is_file():
            s = f.suffix.lower()
            if s == ".futa":
                return "custom_futas"
            if s in [".spouse", ".wife"]:
                return "custom_wives"
            if s == ".bedroom":
                return "custom_bedrooms"

    return None

def write_manifests_for_category(category_dir: Path) -> int:
    """Generates clean _manifest.txt files for category root and all subdirectories."""
    manifest_count = 0
    if not category_dir.is_dir():
        return 0

    top_dirs = sorted([d.name for d in category_dir.iterdir() if d.is_dir() and not d.name.startswith(".")])
    if top_dirs:
        (category_dir / "_manifest.txt").write_text("\n".join(top_dirs) + "\n", encoding="utf-8")
        manifest_count += 1

    for pack_dir in category_dir.iterdir():
        if pack_dir.is_dir() and not pack_dir.name.startswith("."):
            for root, dirs, files in os.walk(pack_dir):
                clean_dirs = sorted([d for d in dirs if not d.startswith(".") and d != "__pycache__"])
                clean_files = sorted([f for f in files if Path(f).suffix.lower() in VALID_EXTENSIONS and f != "_manifest.txt" and not f.startswith(".") and not f.endswith("~")])
                entries = clean_dirs + clean_files
                if entries:
                    (Path(root) / "_manifest.txt").write_text("\n".join(entries) + "\n", encoding="utf-8")
                    manifest_count += 1

    return manifest_count

def convert_15_to_modroom(source_path: Path, dest_dir: Path, clean_dest: bool = False, verbose: bool = True) -> Dict[str, int]:
    """
    Extracts, routes, and organizes v1.5 mod packs into ModRoom architecture.
    Returns summary statistics dictionary.
    """
    stats = {
        "custom_futas": 0,
        "custom_wives": 0,
        "custom_bedrooms": 0,
        "files_copied": 0,
        "bloat_skipped": 0,
        "manifests_generated": 0
    }

    source_path = source_path.resolve()
    dest_dir = dest_dir.resolve()

    if clean_dest and dest_dir.exists():
        for cat in ["custom_futas", "custom_wives", "custom_bedrooms"]:
            c_path = dest_dir / cat
            if c_path.exists():
                shutil.rmtree(c_path)

    dest_dir.mkdir(parents=True, exist_ok=True)
    for cat in ["custom_futas", "custom_wives", "custom_bedrooms"]:
        (dest_dir / cat).mkdir(parents=True, exist_ok=True)

    extracted_temp = None
    if source_path.is_file() and source_path.suffix.lower() == ".zip":
        import tempfile
        extracted_temp = Path(tempfile.mkdtemp(prefix="wb_15_conv_"))
        if verbose:
            print(f"[*] Unpacking source .zip archive: {source_path.name}...")
        with zipfile.ZipFile(source_path, 'r') as z:
            z.extractall(extracted_temp)
        search_root = extracted_temp
    else:
        search_root = source_path

    packs_to_process = []
    custom_dir = search_root / "custom"
    if custom_dir.is_dir():
        for item in sorted(custom_dir.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                packs_to_process.append(item)
    elif detect_pack_category(search_root):
        packs_to_process.append(search_root)
    else:
        for item in sorted(search_root.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                if detect_pack_category(item):
                    packs_to_process.append(item)

    if verbose:
        print(f"[*] Discovered {len(packs_to_process)} mod pack(s) to convert.")

    used_names: Dict[str, Set[str]] = {
        "custom_futas": set(),
        "custom_wives": set(),
        "custom_bedrooms": set()
    }

    for pack in packs_to_process:
        cat = detect_pack_category(pack)
        if not cat:
            if verbose:
                print(f"[-] Notice: Skipping '{pack.name}' (no .futa, .spouse, or .bedroom header found).")
            continue

        display_name = extract_pack_display_name(pack)
        clean_name = sanitize_name(display_name)

        if clean_name in used_names[cat]:
            clean_name = f"{clean_name}_{sanitize_name(pack.name)}"
        used_names[cat].add(clean_name)

        target_pack_dir = dest_dir / cat / clean_name
        target_pack_dir.mkdir(parents=True, exist_ok=True)

        copied_for_pack = 0
        for root, dirs, files in os.walk(pack):
            rel_p = Path(root).relative_to(pack)
            target_sub = target_pack_dir / rel_p
            target_sub.mkdir(parents=True, exist_ok=True)

            for f in files:
                fpath = Path(root) / f
                ext = fpath.suffix.lower()

                if ext in IGNORED_PROJECT_EXTENSIONS or fpath.name.startswith(".") or fpath.name.endswith("~"):
                    stats["bloat_skipped"] += 1
                    continue

                if ext in VALID_EXTENSIONS and fpath.name.lower() != "_manifest.txt":
                    dest_file = target_sub / fpath.name.lower()
                    shutil.copy2(fpath, dest_file)
                    stats["files_copied"] += 1
                    copied_for_pack += 1

        stats[cat] += 1
        if verbose:
            tag = "Lover" if cat == "custom_futas" else ("Partner" if cat == "custom_wives" else "Bedroom")
            print(f"[+] Converted {tag:7s}: {pack.name:25s} -> {cat}/{clean_name} ({copied_for_pack} files)")

    if verbose:
        print("[*] Generating Android & PC _manifest.txt index files...")
    for cat in ["custom_futas", "custom_wives", "custom_bedrooms"]:
        stats["manifests_generated"] += write_manifests_for_category(dest_dir / cat)

    if extracted_temp and extracted_temp.exists():
        shutil.rmtree(extracted_temp, ignore_errors=True)

    return stats

def main():
    parser = argparse.ArgumentParser(description="Convert Wife's Bedroom v1.5 mods to ModRoom architecture.")
    parser.add_argument("input", nargs="?", help="Path to v1.5 mod folder, custom/ directory, or .zip archive.")
    parser.add_argument("-d", "--dest", help="Destination directory (ModRoom game folder or export folder).")
    parser.add_argument("--clean", action="store_true", help="Clean destination category folders before converting.")
    parser.add_argument("-y", "--yes", action="store_true", help="Non-interactive execution (accept defaults).")
    args = parser.parse_args()

    tool_dir = Path(__file__).resolve().parent
    input_dir = tool_dir / "input"
    output_dir = tool_dir / "output" / "ModRoom_Mods"

    print("=" * 70)
    print("      WB 1.5 TO MODROOM MOD CONVERTER v1.0")
    print("=" * 70)

    source_path = None
    if args.input:
        cand = Path(args.input).resolve()
        if cand.exists():
            source_path = cand

    if not source_path:
        if input_dir.is_dir():
            for item in input_dir.iterdir():
                if item.name.startswith("."):
                    continue
                if item.is_dir() or item.suffix.lower() == ".zip":
                    source_path = item.resolve()
                    break



    if not source_path:
        if not args.yes and sys.stdin and sys.stdin.isatty():
            try:
                user_in = input("Enter path to v1.5 mod folder or .zip file: ").strip().strip('"').strip("'")
                if user_in and Path(user_in).exists():
                    source_path = Path(user_in).resolve()
            except Exception:
                pass

    if not source_path or not source_path.exists():
        print("[!] Error: No valid v1.5 mod folder or .zip archive provided.")
        print("    Please drag your mod folder onto Convert_1.5_to_ModRoom.bat")
        print("    or place your files inside the input/ folder.")
        sys.exit(1)

    dest_dir = Path(args.dest).resolve() if args.dest else output_dir

    print(f"[*] Source Mods  : {source_path}")
    print(f"[*] Destination  : {dest_dir}\n")

    stats = convert_15_to_modroom(source_path, dest_dir, clean_dest=args.clean, verbose=True)

    print("\n" + "=" * 70)
    print("CONVERSION COMPLETE - SUMMARY REPORT")
    print("=" * 70)
    print(f"  Lovers Converted (custom_futas)    : {stats['custom_futas']}")
    print(f"  Partners Converted (custom_wives)  : {stats['custom_wives']}")
    print(f"  Bedrooms Converted (custom_bedrooms): {stats['custom_bedrooms']}")
    print(f"  Total Assets Integrated           : {stats['files_copied']}")
    print(f"  Raw Art Project Files Stripped    : {stats['bloat_skipped']}")
    print(f"  Manifest Indexes Generated        : {stats['manifests_generated']}")
    print("-" * 70)
    print(f"[+] Converted mods ready at:\n    {dest_dir}")
    print("=" * 70)

if __name__ == "__main__":
    main()
