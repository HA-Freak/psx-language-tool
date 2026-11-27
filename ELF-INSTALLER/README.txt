PSX Language Tool  (PSX_LANGUAGE_TOOL.ELF)
==========================================

Installs German, English, Polish or Spanish on a PSX (DESR). Start it with wLaunchELF
(e.g. from a USB stick). Controller in port 1:
D-pad up/down = select, X or O = run, START = confirm, any other button = cancel.
The bar at the bottom of the screen always shows the buttons that apply.
See screen_preview.png for what the screens look like.

The model series is recognised automatically on hdd0:__system:

  DESR-5500/5700/7500/7700  (firmware 2.x, has /dic)
      Install = XMB menus and dialogs (xosd/packages, 399 files)
                + button labels (dic/jp.dic)
  DESR-5000/5100/7000/7100  (firmware 1.31, no /dic)
      Install = XMB menus and dialogs (xosd/packages, 106 files)

All texts are built into the ELF - nothing else has to be copied.

Backup
------
Before the FIRST install the tool copies every file it will overwrite to
  hdd0:__system/langtool_bak/        (+ manifest.txt with the file list)
and, on the 5500 series, the original button labels to dic/jp.dic.bak.
The backup is written once and never overwritten, so
"Restore backup (state before first install)" always returns to exactly
that state (files the tool added are removed again).
"Create backup now" makes the backup without installing anything.

Every write is read back and compared. If errors are reported, run
"Restore backup".

If the firmware does not match the one the texts were made for
(1.31 / 2.11), a warning is shown before installing.

Menu
----
  Install German / English / Polish / Spanish
  Restore backup (state before first install)
  Restore Japanese button labels only     (5500 series only)
  Create backup now
  Refresh status
  Power off PSX

Status shows the model, firmware, installed XMB language, jp.dic language
and whether backups exist.

Rebuild: python build.py  (see README.md)
         (see README.md in the project root)
