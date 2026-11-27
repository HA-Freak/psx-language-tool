# PSX Language Tool

German, English, Polish and Spanish translations of the XMB for the Sony PSX (DESR), plus an
installer ELF that runs on the PSX itself.

The repository contains **no Sony files** - only translation tables, scripts and the
ELF source. The language folders and the ELF are built from your own copies of the
source files.

## Screenshots

`PSX_LANGUAGE_TOOL.ELF` on a DESR-5500 (rendered by the PC host test from the same image the tool sends to the
TV):

| Main menu | Confirmation |
|---|---|
| ![Main menu](docs/screenshots/1_main_menu.png) | ![Confirmation](docs/screenshots/2_confirm.png) |
| **Installing (backup first)** | **Done** |
| ![Installing](docs/screenshots/3_installing.png) | ![Done](docs/screenshots/4_done.png) |

## Building

Needs only Python 3.8+ (Windows, Linux or macOS).

1. Download the EN package `PSX_SystemFiles_EN_v1.3_Final.zip` of
   [RepairBox-PSX-HDD-Setup](https://github.com/DanielFergisz/RepairBox-PSX-HDD-Setup)
   ([direct link](https://drive.google.com/file/d/1FjzAhc510617HnPV5F-vRG8m4WtTbchO/view))
   and put it into `sources/` - or just leave it in your Downloads folder.
2. Run

   ```
   python build.py
   ```

That's all. It builds the language folders from the package's original system files
(`RepairBox-PSX1/PSX2-SystemFiles/__system`), checks every file against
`tools/expected.sha1` and builds `ELF-INSTALLER/PSX_LANGUAGE_TOOL.ELF`. The first run
downloads the [ps2dev](https://github.com/ps2dev/ps2dev) v2.0.0 toolchain (~270 MB) into
`tools/ps2dev`. Options: `python build.py PATH_TO_ZIP`, `--no-elf`, `--no-check`.

Result:

| Folder | Content |
|---|---|
| `DESR-5000-5100-7000-7100 XMB GER/ENG/POL/ESP` | XMB files for firmware 1.31 (`xosd/packages/...` on `hdd0:__system`) |
| `DESR-5500-5700-7500-7700 XMB GER/ENG/POL/ESP` | XMB package folders for firmware 2.11 (`hdd0:__system/xosd/packages/`) |
| `SYSTEM-DIC GER/ENG/POL/ESP` | button labels `hdd0:__system/dic/jp.dic` (5500 series) |
| `ELF-INSTALLER/PSX_LANGUAGE_TOOL.ELF` | installs everything with backup/restore, see `ELF-INSTALLER/README.txt` |

## In the repository

| Path | Content |
|---|---|
| `tools/translation` | `eng5000.patch`, `eng5500.patch` (English texts as a patch for the original files - only the new texts, no Sony text), `de*.tsv`, `pl*.tsv`, `es*.tsv` and the scripts that apply them |
| `tools/sysdic` | builds the button-label `jp.dic` files |
| `tools/elf` | ELF source (`gui.c`), pack/check scripts, font generator, PC host test |
| `build.py` | one-command build (calls `tools/build_all.py` and `tools/elf/build.py`) |
| `tools/build_all.py`, `tools/expected.sha1` | language folders and their reference checksums |

## Testing on the PC

`tools/elf/hosttest` compiles `gui.c` for Windows (MSYS2 i686 gcc + zlib) with stubs for
the PS2 libraries and runs install / backup / restore scenarios against copies of the
package's `__system` folders (`run.py`, uses `build/package` from `build_all.py`).
Set `SCRSHOT` to save every screen as PPM.

## Credits

- PSX system files (base for all languages):
  [RepairBox-PSX-HDD-Setup](https://github.com/DanielFergisz/RepairBox-PSX-HDD-Setup)
  by DanielFergisz (RepairBox.pl)
- English texts: based on the English community XMB mods, cleaned up
- Font: Cascadia Mono (SIL Open Font License)
- Toolchain: [ps2dev](https://github.com/ps2dev/ps2dev), gsKit, zlib

The built folders and the ELF contain Sony-derived files - keep them for private use.
