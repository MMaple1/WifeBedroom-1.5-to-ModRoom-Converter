#!/usr/bin/env python3
"""
WB 1.5 to Modded Converter v1.1
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
from typing import Dict, List, Tuple, Optional, Set, Union
import atexit
import hashlib
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent / "core"))
import wbconv  # shared, tested conversion core (PNG strips, descriptors, ModRoom rules, safe zip/publish)

# Pack names can contain characters a Windows console cannot encode; never let printing one end the run.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass

VALID_EXTENSIONS = {
    ".png", ".ogg", ".wav", ".mp3", ".json",
    ".futa", ".spouse", ".wife", ".bedroom",
    ".ini", ".jpg", ".jpeg", ".gif", ".webp"
}

IGNORED_PROJECT_EXTENSIONS = {
    ".aseprite", ".ase", ".clip", ".pdn", ".kra",
    ".psd", ".xcf", ".blend", ".zip", ".rar", ".7z",
    ".tar", ".gz", ".bak", ".tmp", ".pdf", ".docx", ".doc"
}

print_progress = wbconv.progress  # shared, throttled bar (kept under the old name)

def sanitize_name(name: str) -> str:
    """Clean, lowercase, filesystem- and manifest-safe identifier (see wbconv.safe_dirname)."""
    return wbconv.safe_dirname(name)

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

def compute_file_sha256(path: Path) -> str:
    """Computes SHA-256 hash of a file for exact asset fingerprinting."""
    try:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""

VARIANT_ATTR_TOKENS = {
    "nude", "clothed", "naked", "underwear", "lingerie", "bikini", "bunnysuit",
    "human", "horse", "horsecock", "equine", "knot", "knotted", "diphallia",
    "shiny", "palette", "oral", "bj", "bbw", "milk", "tail", "alt"
}

def extract_variant_tokens(name: str):
    words = set(re.findall(r"[a-zA-Z0-9]+", str(name).lower()))
    return words & VARIANT_ATTR_TOKENS

def normalize_pack_slug(name: str) -> str:
    """Normalizes a folder or character name into a clean comparison slug (Tier 1).
    CRITICAL: Preserves distinguishing attribute tokens (nude, clothed, knot, horse, etc.)
    so distinct variants of the same character are NEVER treated as duplicates."""
    s = re.sub(r"\b(COMM|V\d+(\.\d+)?|WIP|BS)\b", "", name, flags=re.I)
    s = re.sub(r"(\s*-\s*copy(\s*\(\d+\))?|\s*\(\d+\)|_copy(\d+)?|_backup|_old)$", "", s, flags=re.I)
    s = re.sub(r'[\\/:*?\"<>|!#~_.-]+', ' ', s).strip().lower()
    return re.sub(r"\s+", "_", s)

def detect_intrinsic_category(pack_path: Path) -> str:
    """Inspects internal files to determine the true intrinsic category of a pack."""
    try:
        files = {f.name.lower() for f in pack_path.iterdir() if f.is_file()}
        if any(w in files for w in ["custom_data.spouse", "custom_data.wife", "custom_wife.ini"]):
            return "custom_wives"
        if any(w in files for w in ["custom_data.futa", "custom_futa.ini"]):
            return "custom_futas"
        if any(w in files for w in ["custom_data.bedroom", "background.png", "custom_background.png"]):
            return "custom_bedrooms"

        if any("wife" in f for f in files) or any("spouse" in f for f in files) or "custom_cowgirl.png" in files:
            return "custom_wives"
        if any("futa" in f for f in files) or "custom_futa_portrait_0.png" in files:
            return "custom_futas"
        if any("bedroom" in f for f in files) or any("room" in f for f in files):
            return "custom_bedrooms"

        for f in files:
            if f.endswith(".futa"):
                return "custom_futas"
            if f.endswith(".spouse") or f.endswith(".wife"):
                return "custom_wives"
            if f.endswith(".bedroom"):
                return "custom_bedrooms"
    except Exception:
        pass
    return "unknown"

def score_pack_canonical(pack_path: Path, cat: str = "", target_is_v15: bool = False, target_arch: str = "deeproom") -> float:
    """Calculates canonical score for duplicate tie-breaking (Tier 3). Higher is preferred."""
    score = 0.0
    valid_exts = {".png", ".ogg", ".wav", ".mp3", ".json", ".futa", ".spouse", ".wife", ".bedroom", ".ini", ".txt"}
    files = [f for f in pack_path.rglob("*") if f.is_file() and f.suffix.lower() in valid_exts]
    score += len(files) * 10.0
    audio_files = [f for f in files if f.suffix.lower() in [".ogg", ".wav", ".mp3"]]
    score += len(audio_files) * 25.0
    file_names = {f.name.lower() for f in files}
    if any("cowgirl" in n for n in file_names):
        score += 30.0
    if any("xray" in n for n in file_names):
        score += 20.0
    name = pack_path.name
    if re.search(r"(\s*-\s*copy|\s*\(\d+\)|_copy|_old|_backup)", name, re.I):
        score -= 50.0
    if name.isdigit() and len(name) >= 7:
        score -= 30.0

    # Category Affinity Bonus & Conflicting Folder Penalty (Ensures wives in custom_wives win over wives in custom_futas)
    intrinsic = detect_intrinsic_category(pack_path)
    if intrinsic != "unknown":
        if cat == intrinsic:
            score += 100.0  # Perfect folder match!
        elif cat == "custom":
            score += 20.0   # Unified format acceptable
        else:
            score -= 100.0  # Severe penalty for misplaced conflicting duplicate!

    # Target Architecture Alignment Bonus
    is_inside_custom_stuff = "custom_stuff" in [part.lower() for part in pack_path.parts]
    if target_is_v15 or target_arch == "v15":
        if cat == "custom":
            score += 50.0
    elif target_arch == "modroom":
        if not is_inside_custom_stuff and cat in ["custom_futas", "custom_wives", "custom_bedrooms"]:
            score += 50.0  # ModRoom v3.3 strictly requires root-level category folders
        elif is_inside_custom_stuff:
            score -= 50.0  # ModRoom v3.3 does not read custom_stuff/
    elif target_arch == "deeproom":
        if is_inside_custom_stuff and cat in ["custom_futas", "custom_wives", "custom_bedrooms"]:
            score += 50.0  # Deeproom 4.0.3 strictly requires custom_stuff/ container
        elif not is_inside_custom_stuff:
            score -= 20.0

    try:
        mtime = max(f.stat().st_mtime for f in files) if files else pack_path.stat().st_mtime
        score += mtime / 1000000000.0
    except Exception:
        pass
    return score

def get_pack_fingerprints(pack_path: Path, cat: str = "") -> dict:
    """Extracts SHA-256 asset fingerprints across characters, bedrooms, SFX/audio, and dialogues (Tier 2)."""
    fps = {}
    try:
        audio_hashes = []
        for f in sorted(pack_path.iterdir()):
            if not f.is_file():
                continue
            fn = f.name.lower()
            ext = f.suffix.lower()
            if fn in ["custom_portrait.png", "custom_futa_portrait_0.png", "custom_wife_portrait_0.png"]:
                fps["portrait"] = compute_file_sha256(f)
            elif fn in ["custom_mating_press.png", "custom_futa_mating_press_0.png", "custom_wife_mating_press_0.png"]:
                fps["mating"] = compute_file_sha256(f)
            elif fn in ["background.png", "custom_background.png"]:
                fps["bg"] = compute_file_sha256(f)
            elif ext in [".ogg", ".wav", ".mp3"] and len(audio_hashes) < 3:
                audio_hashes.append(compute_file_sha256(f))
            elif ext == ".json" and "dialogue" in cat:
                fps["dialogue"] = compute_file_sha256(f)
        if audio_hashes:
            fps["audio_primary"] = audio_hashes[0]
    except Exception:
        pass
    return fps

def is_compatible_category(cat1: str, cat2: str) -> bool:
    """Determines whether two categories can contain duplicate variants (e.g. custom/ vs custom_wives/).
    CRITICAL: custom_futas (Lovers/Tops) and custom_wives (Partners/Bottoms) are distinct gameplay roles
    and must NEVER cluster as duplicates of each other."""
    if cat1 == cat2:
        return True
    if (cat1 == "custom" and cat2 in ["custom_futas", "custom_wives"]) or (cat2 == "custom" and cat1 in ["custom_futas", "custom_wives"]):
        return True
    if (cat1 == "custom" and cat2 == "custom_bedrooms") or (cat2 == "custom" and cat1 == "custom_bedrooms"):
        return True
    if cat1 in {"custom_sounds", "custom_music"} and cat2 in {"custom_sounds", "custom_music"}:
        return True
    if cat1 in {"dialogue", "dialogue_packs", "custom_dialogues"} and cat2 in {"dialogue", "dialogue_packs", "custom_dialogues"}:
        return True
    return False

def quarantine_duplicate_packs(packs_to_convert: list, quarantine_dir: Path, target_is_v15: bool = False, target_arch: str = "deeproom", verbose: bool = True):
    """
    3-Tier Cross-Folder & Cross-Category Duplicate Detection & Quarantine Engine:
    Clusters discovered packs across folders/categories, isolates duplicates into '!duplicates', and writes DUPLICATES_REPORT.txt.
    Returns (retained_packs, quarantined_count, list_of_quarantined).
    """
    if len(packs_to_convert) <= 1:
        return packs_to_convert, 0, []

    quarantine_dir = Path(quarantine_dir)

    pack_data = []
    for n_done, (pack_path, cat) in enumerate(packs_to_convert, 1):
        if verbose:
            print_progress(n_done, len(packs_to_convert), prefix="Duplicate check")
        f_slug = normalize_pack_slug(pack_path.name)
        d_name = extract_pack_display_name(pack_path)
        i_slug = normalize_pack_slug(d_name) if d_name else ""
        fps = get_pack_fingerprints(pack_path, cat=cat)
        score = score_pack_canonical(pack_path, cat=cat, target_is_v15=target_is_v15, target_arch=target_arch)
        pack_data.append({
            "path": pack_path,
            "cat": cat,
            "folder_slug": f_slug,
            "info_slug": i_slug,
            "fps": fps,
            "score": score
        })

    n = len(pack_data)
    parent = list(range(n))
    def find(i):
        if parent[i] == i: return i
        parent[i] = find(parent[i])
        return parent[i]
    def union(i, j):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    pair_reasons = {}
    for i in range(n):
        for j in range(i + 1, n):
            pi = pack_data[i]
            pj = pack_data[j]
            if not is_compatible_category(pi["cat"], pj["cat"]):
                continue

            # Variant Attribute Guard: If two characters have divergent attributes (e.g. nude vs clothed, horse vs knot),
            # they are distinct variants authored for different gameplay preferences and must NEVER be quarantined as duplicates
            v_i = extract_variant_tokens(pi["path"].name) | extract_variant_tokens(pi.get("info_slug", ""))
            v_j = extract_variant_tokens(pj["path"].name) | extract_variant_tokens(pj.get("info_slug", ""))
            if v_i != v_j and (v_i or v_j):
                continue

            is_dup = False
            reason = ""

            # Tier 2: Fingerprint match (SHA-256 of key artwork files)
            # Only identical visual sprites (portrait AND mating press) prove duplicate identity;
            # shared audio or dialogue files must never cause different visual variants to be quarantined
            fps_i, fps_j = pi["fps"], pj["fps"]
            if "mating" in fps_i and "mating" in fps_j and fps_i["mating"] and fps_i["mating"] == fps_j["mating"]:
                if "portrait" in fps_i and "portrait" in fps_j and fps_i["portrait"] and fps_i["portrait"] == fps_j["portrait"]:
                    is_dup = True
                    reason = "Tier 2 Asset Match (Identical portrait & mating sheet SHA-256)"
                elif "portrait" not in fps_i or "portrait" not in fps_j:
                    is_dup = True
                    reason = "Tier 2 Asset Match (Identical mating sheet SHA-256)"
            elif "bg" in fps_i and "bg" in fps_j and fps_i["bg"] and fps_i["bg"] == fps_j["bg"]:
                is_dup = True
                reason = "Tier 2 Asset Match (Identical background image SHA-256)"

            GENERIC_SLUGS = {"example", "custom", "custom_character", "character", "wife", "partner", "futa", "lover", "not_found", "unknown", "unnamed", "none", "new_pack", "template"}
            if not is_dup:
                if pi["folder_slug"] and pi["folder_slug"] == pj["folder_slug"]:
                    is_dup = True
                    reason = f"Tier 1 Name Match (Normalized slug '{pi['folder_slug']}')"
                elif pi["info_slug"] and pi["info_slug"] not in GENERIC_SLUGS and (pi["info_slug"] == pj["folder_slug"] or pi["info_slug"] == pj["info_slug"]):
                    is_dup = True
                    reason = f"Tier 1 Metadata Match (Descriptor [info] name '{pi['info_slug']}')"
                elif pj["info_slug"] and pj["info_slug"] not in GENERIC_SLUGS and pj["info_slug"] == pi["folder_slug"]:
                    is_dup = True
                    reason = f"Tier 1 Metadata Match (Descriptor [info] name '{pj['info_slug']}')"

            if is_dup:
                union(i, j)
                pair_reasons[(min(i, j), max(i, j))] = reason

    clusters = {}
    for i in range(n):
        r = find(i)
        clusters.setdefault(r, []).append(pack_data[i])

    retained_packs = []
    quarantined = []
    quarantined_report_lines = []

    for r, group in clusters.items():
        if len(group) == 1:
            retained_packs.append((group[0]["path"], group[0]["cat"]))
        else:
            group.sort(key=lambda x: x["score"], reverse=True)
            winner = group[0]
            retained_packs.append((winner["path"], winner["cat"]))
            for dup in group[1:]:
                try:
                    quarantined.append((dup["path"], winner["path"]))
                    reason = f"Duplicate of [{winner['cat']}] '{winner['path'].name}' (Score {winner['score']:.1f} vs {dup['score']:.1f})"
                    quarantined_report_lines.append(f"[{dup['cat']}] {dup['path'].name} -> Quarantined (Winner: [{winner['cat']}] {winner['path'].name}) | Reason: {reason}")
                    if verbose:
                        wbconv.say(f"[!] Duplicate Quarantine: Isolated duplicate '[{dup['cat']}] {dup['path'].name}' (Winner: '[{winner['cat']}] {winner['path'].name}').")
                except Exception as m_err:
                    if verbose:
                        wbconv.say(f"[!] Notice: Failed to isolate duplicate '{dup['path'].name}': {m_err}")

    return retained_packs, len(quarantined), quarantined

def convert_15_to_modroom(sources: Union[Path, List[Path]], dest_dir: Path, target_arch: str = "both", clean_dest: bool = False, verbose: bool = True, quarantine_duplicates: bool = True, approximate: bool = False, dry_run: bool = False, report=None) -> Dict[str, int]:
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
        "manifests_generated": 0,
        "skipped_packs": 0
    }

    if isinstance(sources, Path):
        source_paths = [sources]
    else:
        source_paths = list(sources)

    dest_dir = dest_dir.resolve()

    target_arch_lower = str(target_arch).lower()
    
    if report is None:
        report = wbconv.Report("WB 1.5 to Modded conversion report")

    # Convert into a staging folder first; the destination is only touched once packs were produced.
    # Deeproom 4.0.3 uses the custom_stuff container, ModRoom the root category folders.
    stage_root = Path(tempfile.mkdtemp(prefix="wb15_to_mod_stage_"))
    temp_dirs_to_clean = [stage_root]
    atexit.register(lambda: [shutil.rmtree(d, ignore_errors=True) for d in temp_dirs_to_clean])
    target_roots = []     # staging roots
    final_roots = []      # (staging root, final root)
    if target_arch_lower in ["deeproom", "both"]:
        cs_stage = stage_root / "deeproom" / "custom_stuff"
        target_roots.append(cs_stage)
        final_roots.append((cs_stage, dest_dir / "custom_stuff"))
    if target_arch_lower in ["modroom", "both"]:
        mr_stage = stage_root / "modroom"
        target_roots.append(mr_stage)
        final_roots.append((mr_stage, dest_dir))

    for r in target_roots:
        for cat in ["custom_futas", "custom_wives", "custom_bedrooms"]:
            (r / cat).mkdir(parents=True, exist_ok=True)

    packs_to_process = []
    for s_path in source_paths:
        source_p = s_path.resolve()
        if not source_p.exists():
            continue
        if source_p.is_file() and source_p.suffix.lower() == ".zip":
            extracted_temp = Path(tempfile.mkdtemp(prefix="wb_15_conv_"))
            temp_dirs_to_clean.append(extracted_temp)
            try:
                with wbconv.Spinner(f"Unpacking {source_p.name}"), zipfile.ZipFile(source_p, 'r') as z:
                    wbconv.safe_extract(z, extracted_temp)
            except (ValueError, zipfile.BadZipFile) as exc:
                print(f"[!] Skipping archive {source_p.name}: {exc}")
                continue
            search_root = extracted_temp
        else:
            search_root = source_p
        if not search_root.is_dir():
            print(f"[!] Skipping {search_root.name}: not a folder or .zip archive")
            continue

        custom_dirs = []
        if (search_root / "custom").is_dir():
            custom_dirs.append(search_root / "custom")
        if (search_root / "custom_stuff" / "custom").is_dir():
            custom_dirs.append(search_root / "custom_stuff" / "custom")

        if custom_dirs:
            for c_dir in custom_dirs:
                for item in sorted(c_dir.iterdir()):
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

    if quarantine_duplicates:
        q_dir = dest_dir / "!duplicates"
        pack_pairs = [(p, detect_pack_category(p) or "custom_futas") for p in packs_to_process]
        retained_pairs, q_count, q_list = quarantine_duplicate_packs(pack_pairs, q_dir, target_is_v15=False, target_arch=target_arch, verbose=verbose)
        packs_to_process = [p for p, _ in retained_pairs]
        for dup_path, winner_path in q_list:
            report.add(dup_path.name, "?", target_arch_lower, wbconv.Result("skipped", notes=[f"duplicate of '{winner_path.name}'"]))
        if q_count > 0 and verbose:
            print(f"[+] Duplicate check: skipped {q_count} duplicate pack(s) (nothing is copied or moved; see the conversion report).")
            print(f"[+] Duplicate check: kept {len(packs_to_process)} unique pack(s).")

    used_names: Dict[str, Set[str]] = {
        "custom_futas": set(),
        "custom_wives": set(),
        "custom_bedrooms": set()
    }

    total_packs = len(packs_to_process)
    for p_idx, pack in enumerate(packs_to_process, 1):
        if verbose:
            print_progress(p_idx, total_packs, prefix="Converting")
        cat = detect_pack_category(pack)
        if not cat:
            if verbose:
                print(f"[-] Notice: Skipping '{pack.name}' (no .futa, .spouse, or .bedroom header found).")
            continue

        display_name = extract_pack_display_name(pack)
        clean_name = sanitize_name(display_name)

        clean_name = wbconv.unique_pack_name(clean_name, pack.name, used_names[cat])
        used_names[cat].add(clean_name)
        converted_any = False

        for target_base in target_roots:
            target_pack_dir = wbconv.make_pack_dir(target_base / cat, clean_name, pack.name)  # falls back to the folder name, then a hash, if the OS refuses a name

            copied_for_pack = 0
            for root, dirs, files in os.walk(pack):
                rel_p = Path(root).relative_to(pack)
                target_sub = target_pack_dir / rel_p
                target_sub.mkdir(parents=True, exist_ok=True)

                for f in files:
                    fpath = Path(root) / f
                    ext = fpath.suffix.lower()
                    fname_lower = fpath.name.lower()

                    if ext in IGNORED_PROJECT_EXTENSIONS or (ext == ".txt" and fname_lower != "_manifest.txt") or fpath.name.startswith(".") or fpath.name.endswith("~"):
                        stats["bloat_skipped"] += 1
                        continue

                    if (ext in VALID_EXTENSIONS or fname_lower == "_manifest.txt") and fname_lower != "_manifest.txt":
                        dest_file = target_sub / fname_lower
                        shutil.copy2(fpath, dest_file)
                        stats["files_copied"] += 1
                        copied_for_pack += 1

            # Strips and descriptor: shared, tested core (frame counts, one descriptor per pack, ModRoom's required sprites)
            arch = "deeproom" if target_base.name == "custom_stuff" else "modroom"
            if cat == "custom_bedrooms":
                report.add(pack.name, "bedroom", arch, wbconv.Result("ok"))
                converted_any = True
                continue
            kind = "futa" if cat == "custom_futas" else "wife"
            res = wbconv.from_v15(target_pack_dir, kind, arch, display_name, approximate=approximate)
            report.add(pack.name, kind, arch, res)
            if res.status == "skipped":
                shutil.rmtree(target_pack_dir, ignore_errors=True)
                if verbose:
                    wbconv.say(f"[-] Skipped   {kind:7s}: {pack.name:25s} -> {arch} ({'; '.join(res.notes + res.skipped)})")
                continue
            if verbose and (res.status != "ok" or res.skipped):
                wbconv.say(f"[~] {res.status:11s}: {pack.name} -> {arch} ({'; '.join(res.converted + res.skipped)})")
            converted_any = True

            # Loose portrait: a single unnumbered *portrait*.png (never an _alt or _0 strip, which have other frame counts)
            if arch == "deeproom" or kind == "futa":
                if not (target_pack_dir / "custom_portrait.png").exists():
                    for f in sorted(target_pack_dir.iterdir()):
                        fl = f.name.lower()
                        if "portrait" in fl and fl.endswith(".png") and "_alt" not in fl and not fl.endswith("_0.png") and fl != "custom_portrait.png":
                            shutil.copy2(f, target_pack_dir / "custom_portrait.png")
                            stats["files_copied"] += 1
                            break

        if not converted_any:
            stats["skipped_packs"] += 1
            continue
        stats[cat] += 1
        if verbose:
            tag = "Lover" if cat == "custom_futas" else ("Partner" if cat == "custom_wives" else "Bedroom")
            arch_note = f" (target: {target_arch_lower})"
            wbconv.say(f"[+] Converted {tag:7s}: {pack.name:25s} -> {cat}/{clean_name}{arch_note} ({copied_for_pack} files)")

    produced = sum(1 for st, _ in final_roots for c in ("custom_futas", "custom_wives", "custom_bedrooms")
                   if (st / c).is_dir() for p in (st / c).iterdir() if p.is_dir())
    if dry_run:
        print(f"[*] Dry run: {produced} pack folder(s) would be written. Nothing was written.")
    elif produced:
        with wbconv.Spinner("Publishing converted packs"):
            for st, final in final_roots:
                for cat in ["custom_futas", "custom_wives", "custom_bedrooms"]:
                    wbconv.publish_category(st / cat, final / cat, clean_dest)
        if verbose:
            print("[*] Generating Android & PC _manifest.txt index files...")
        for _, final in final_roots:
            for cat in ["custom_futas", "custom_wives", "custom_bedrooms"]:
                if (final / cat).is_dir():
                    stats["manifests_generated"] += write_manifests_for_category(final / cat)
    else:
        print("[!] No pack was converted; the destination was not touched.")

    for tmp_d in temp_dirs_to_clean:
        if tmp_d.exists():
            shutil.rmtree(tmp_d, ignore_errors=True)

    stats["report"] = report
    return stats

def main():
    if sys.version_info < (3, 8):
        print("[!] Error: Python 3.8 or higher is required. Please update Python.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="WB 1.5 to Modded Converter: Convert v1.5 custom mods into Deeproom 4.0 or ModRoom 1.4 architecture"
    )
    parser.add_argument("inputs", nargs="*", help="Path(s) to v1.5 mod folders, custom/ directory, character packs, or .zip archives.")
    parser.add_argument("-t", "--target", choices=["deeproom", "modroom", "both"], help="Target output architecture: deeproom (standard naming), modroom (v3.3 _0.png naming), or both.")
    parser.add_argument("-d", "--dest", help="Destination directory (ModRoom/Deeproom game folder or export folder).")
    parser.add_argument("--clean", action="store_true", help="Clean destination category folders before converting.")
    parser.add_argument("--approximate", action="store_true", help="Also convert strips whose frame counts differ by dropping frames (first N kept); listed as 'approximate' in the report.")
    parser.add_argument("--no-approximate", action="store_true", help="Disallow lossy frame reduction (default: safe)")
    parser.add_argument("--dry-run", action="store_true", help="Convert into a temporary folder and write only the report; nothing is written to the destination.")
    parser.add_argument("-y", "--yes", action="store_true", help="Non-interactive execution (accept defaults).")
    parser.add_argument("--quarantine-duplicates", action="store_true", default=None, help="Automatically detect and quarantine duplicate custom character/room folders (default: True)")
    parser.add_argument("--no-quarantine-duplicates", action="store_true", default=None, help="Disable duplicate custom folder quarantine")

    args = parser.parse_args()

    tool_dir = Path(__file__).resolve().parent
    input_dir = tool_dir / "input"

    print("=" * 70)
    print("      WB 1.5 TO MODDED CONVERTER v1.2")
    print("=" * 70)

    source_paths = []
    if args.inputs:
        for inp in args.inputs:
            cand = Path(inp).resolve()
            if cand.exists():
                source_paths.append(cand)

    if not source_paths and input_dir.is_dir():
        for item in sorted(input_dir.iterdir()):
            if not item.name.startswith("."):
                source_paths.append(item.resolve())

    if not source_paths:
        if not args.yes and sys.stdin and sys.stdin.isatty():
            try:
                user_in = input("Enter path to v1.5 mod folder or .zip file: ").strip().strip('"').strip("'")
                if user_in and Path(user_in).exists():
                    source_paths.append(Path(user_in).resolve())
            except Exception:
                pass

    if not source_paths:
        print("[!] Error: No valid v1.5 mod folder or .zip archive provided.")
        print("    Please drag your mod folder onto Convert_from_WB_1.5.bat")
        print("    or place your files inside the input/ folder.")
        sys.exit(1)

    approximate_enabled = False  # Default to safe
    if args.no_approximate:
        approximate_enabled = False
    elif args.approximate:
        approximate_enabled = True
    elif not args.yes and sys.stdin and sys.stdin.isatty():
        try:
            ans_app = input("Allow approximate frame reduction (drop extra frames for legacy targets)? [y/N]: ").strip().lower()
            if ans_app:
                approximate_enabled = ans_app.startswith("y")
        except Exception:
            approximate_enabled = False

    chosen_target = getattr(args, "target", None)
    if not chosen_target:
        if args.yes or not (sys.stdin and sys.stdin.isatty()):
            chosen_target = "both"
        else:
            print("\nSelect Target Output Architecture:")
            print("  [1] Deeproom 4.0 Standard  (output/Deeproom_Mods/ - standard unnumbered filenames)")
            print("  [2] ModRoom v3.3 Legacy    (output/ModRoom_Mods/ - legacy _0.png filenames)")
            print("  [3] Both Architectures     (Exports both side-by-side) [DEFAULT]")
            try:
                t_in = input("Selection [1-3, default: 3]: ").strip()
                t_map = {"1": "deeproom", "2": "modroom", "3": "both"}
                chosen_target = t_map.get(t_in, "both")
            except Exception:
                chosen_target = "both"

    quarantine_enabled = True  # Default to ON
    if args.no_quarantine_duplicates:
        quarantine_enabled = False
    elif args.quarantine_duplicates:
        quarantine_enabled = True
    elif not args.yes and sys.stdin and sys.stdin.isatty():
        try:
            ans = input("Detect and quarantine duplicate custom assets across packs? [Y/n]: ").strip().lower()
            if ans:
                quarantine_enabled = ans.startswith("y")
        except Exception:
            quarantine_enabled = True

    print(f"[*] Duplicate Quarantine : {'ENABLED [Default]' if quarantine_enabled else 'DISABLED'}")


    targets_to_run = []
    if args.dest and chosen_target == "both":
        targets_to_run.append(("deeproom", Path(args.dest).resolve() / "Deeproom_Mods"))
        targets_to_run.append(("modroom", Path(args.dest).resolve() / "ModRoom_Mods"))
    elif args.dest:
        targets_to_run.append((chosen_target, Path(args.dest).resolve()))
    elif chosen_target == "both":
        targets_to_run.append(("deeproom", tool_dir / "output" / "Deeproom_Mods"))
        targets_to_run.append(("modroom", tool_dir / "output" / "ModRoom_Mods"))
    elif chosen_target == "modroom":
        targets_to_run.append(("modroom", tool_dir / "output" / "ModRoom_Mods"))
    else:
        targets_to_run.append(("deeproom", tool_dir / "output" / "Deeproom_Mods"))

    all_stats = []
    shared_report = wbconv.Report("WB 1.5 to Modded conversion report")
    for arch_mode, dest_dir in targets_to_run:
        print(f"\n[*] Source Mods  : {[p.name for p in source_paths]}")
        print(f"[*] Target Arch  : {arch_mode.upper()} Architecture")
        print(f"[*] Destination  : {dest_dir}\n")
        st = convert_15_to_modroom(source_paths, dest_dir, target_arch=arch_mode, clean_dest=args.clean, verbose=True, quarantine_duplicates=quarantine_enabled,
                                   approximate=approximate_enabled, dry_run=args.dry_run, report=shared_report)
        all_stats.append((arch_mode, dest_dir, st))

    report_path = tool_dir / "output" / "conversion_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    shared_report.write(report_path)
    tot_skipped = sum(s["skipped_packs"] for _, _, s in all_stats)
    tot_futas = sum(s["custom_futas"] for _, _, s in all_stats)
    tot_wives = sum(s["custom_wives"] for _, _, s in all_stats)
    tot_beds = sum(s["custom_bedrooms"] for _, _, s in all_stats)
    tot_files = sum(s["files_copied"] for _, _, s in all_stats)
    tot_bloat = sum(s["bloat_skipped"] for _, _, s in all_stats)
    tot_mani = sum(s["manifests_generated"] for _, _, s in all_stats)

    target_display = {
        "deeproom": "Deeproom 4.0.3 Kiwami (custom_stuff/ Container)",
        "modroom": "ModRoom v3.3 (Root Categories; partner strips padded to ModRoom's frame counts)",
        "both": "Dual Side-by-Side (Deeproom 4.0.3 & ModRoom v3.3)"
    }.get(chosen_target, chosen_target.upper())

    print("\n" + "=" * 70)
    print("              MOD CONVERSION COMPLETE — SUMMARY CARD")
    print("=" * 70)
    print(f"  Target Architecture   : {target_display}")
    print(f"  Lovers Converted      : {tot_futas:,} Pack(s) (custom_futas directory)")
    print(f"  Partners Converted    : {tot_wives:,} Pack(s) (custom_wives directory)")
    print(f"  Bedrooms Converted    : {tot_beds:,} Pack(s) (custom_bedrooms directory)")
    print(f"  Total Assets Packaged : {tot_files:,} File(s) Integrated")
    print(f"  Raw Art Files Stripped: {tot_bloat:,} Project File(s) (.aseprite, .psd, .clip, etc.)")
    counts = shared_report.counts()
    print(f"  Conversion Quality    : " + (", ".join(f"{v} {k}" for k, v in sorted(counts.items())) or "nothing converted"))
    print(f"  Packs Not Converted   : {tot_skipped:,} (see the conversion report)")
    print(f"  Conversion Report     : {report_path}")
    print(f"  Manifest Indexes Built: {tot_mani:,} _manifest.txt File(s) Generated")
    print(f"  Duplicate Quarantine  : {'ENABLED' if quarantine_enabled else 'DISABLED'}")
    print("  Output Location(s)    :")
    for arch_mode, d, _ in all_stats:
        print(f"    - [{arch_mode.upper()}]: {d}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
