# WB 1.5 to Modded Mod Converter

This converter takes character and room mods made for Wife's Bedroom v1.5 and turns them into split-folder formats that newer modded engines (Deeproom 4.0.3 Kiwami and ModRoom v3.3) can load.

## Start here

1. Make sure Python is installed (free from python.org; check the box to add Python to PATH).
2. Drag your mod folder (or `.zip` file) onto `Convert_from_WB_1.5.bat`, or put it in the `input/` folder first (if both are empty, it asks for a path).
3. A command window opens. Press Enter for each question to accept the defaults.
4. When finished, press any key to close the window. Converted mods will be in the `output/` folder next to the `.bat` file.

Copy the contents of `output/Deeproom_Mods/custom_stuff/` into your Deeproom game directory, or `output/ModRoom_Mods/` into your ModRoom game directory.

**Troubleshooting:** Open `output/conversion_report.md` in any text editor. It lists every character and notes whether it was converted, padded, approximated, or skipped. A line saying *skipped* means that character was excluded intentionally, with the reason beside it. If the window closes too fast, open Command Prompt in this folder and run `python WB_1.5_to_Modded.py`.

## The questions it asks

- **Target architecture:** Choose which game format to build: Deeproom (`1`), ModRoom (`2`), or **Both** (`3` or Enter). The default is **both**.
- **Approximate mode (`[y/N]`):** Asks whether to allow lossy frame reduction (such as trimming X-ray strips). The default is **No** (`N`), preserving original frames safely.
- **Skip duplicate packs (`[Y/n]`):** If the same character appears more than once, only the best copy is converted; the others are listed in the report. The default is **Yes**. Nothing in your mod folder is changed.

## What you get

- **`output/Deeproom_Mods/custom_stuff/`**: Mods formatted for Deeproom 4.0.3.
- **`output/ModRoom_Mods/`**: Mods formatted for ModRoom v3.3.
- **`output/conversion_report.md`**: A detailed report tracking what was converted exactly, padded, approximated, or skipped.
- **Dry run output**: Running with `--dry-run` processes files in temporary folders and writes only the conversion report, making no changes to your output game folders.

## Command line

```bash
python WB_1.5_to_Modded.py -t both input_folder
python WB_1.5_to_Modded.py -t deeproom -d "C:/Games/Deeproom" -y pack.zip
python WB_1.5_to_Modded.py -t modroom --approximate input_folder
python WB_1.5_to_Modded.py --dry-run input_folder
```

See DETAILS.md for all options.

## Partners' deepthroat too high in Deeproom?

Partners converted for Deeproom with a version older than 2026-11-17 got a `[deepthroat]` block that draws the deepthroat sprite 66-70 px too high. Drag your Deeproom `custom_stuff/custom_wives` folder onto `Repair_Deepthroat.bat` (or run `python Repair_Deepthroat.py "<folder>"`, then again with `--apply`). It lists what it would fix first, only touches blocks the old converter wrote, and saves the originals in a zip next to the folder.

For full technical details, frame counts, padding and engine rules, see `DETAILS.md`.
