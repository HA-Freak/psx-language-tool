Translation tools  (base = "DESR-5500-5700-7500-7700 XMB ENG")
=================

Full build from the source archives: python tools/build_all.py (see README.md).
It creates the ENG folders from the original English mods with
  en.tsv / en5000.tsv  (cleaned English texts)  and  fixups.tsv  (two 5500 dic
  files with repaired quotes: fixups.py make/apply),
then GER/POL as described below. After changing the ENG folder by hand:
  python make_table.py SOURCE_ENG ENG en.tsv   and update tools/expected.sha1.

The English mod folder is the master. The other languages are generated from it:

  cd tools/translation
  python build_lang.py "../../DESR-5500-5700-7500-7700 XMB ENG" de.tsv "../../DESR-5500-5700-7500-7700 XMB GER"
  python build_lang.py "../../DESR-5500-5700-7500-7700 XMB ENG" pl.tsv "../../DESR-5500-5700-7500-7700 XMB POL" --ascii
  python verify.py ../..          (XML parse + dic quote check, both series)

DESR-5000/5100/7000/7100 (firmware 1.31, texts live directly in the xml files,
no system dictionary needed):
  python build_lang.py "../../DESR-5000-5100-7000-7100 XMB ENG" de5000.tsv "../../DESR-5000-5100-7000-7100 XMB GER"
  python build_lang.py "../../DESR-5000-5100-7000-7100 XMB ENG" pl5000.tsv "../../DESR-5000-5100-7000-7100 XMB POL" --ascii
  (--ascii for safety. The 1.31 font in the RepairBox PSX1 system files does
   contain all Polish letters - drop --ascii if the unit uses that font.)
  The 5000 ENG folder is a cleaned version of the machine-translated mod;
  legacy/desr5000/ holds the source texts and the one-time conversion script.

--ascii: the PSX system font has no a/c/e-ogonek, l-stroke, n/s/z-acute, z-dot.
         pl.tsv keeps correct Polish; the build replaces those letters (o-acute stays).

de.tsv / pl.tsv  -  one row per text:  file <TAB> id <TAB> English <TAB> translation
           (real line breaks inside a value are written as <CRLF> / <LF>)

Workflow
  * Change an English text  -> edit the ENG folder directly, then update the
    English AND German column of that row in de.tsv. build_lang.py reports rows
    whose English no longer matches as STALE (and keeps English there).
  * Change a translation    -> edit only the last column in de.tsv / pl.tsv.
  * New text location       -> add a row (file path relative to the mod folder,
    id = dic key, "s<n>" for the n-th str/label in an xml, or the .sys key).
  * python make_table.py ENG GER de.tsv  regenerates de.tsv from two finished
    folders (e.g. after editing GER files by hand).

psxtext.py  shared parsing helpers
legacy/     original pipeline (built from the machine-translated source mod,
            which has been deleted) - kept for reference only
