#!/bin/sh
# Builds PSX_LANGUAGE_TOOL.ELF with the bundled toolchain in ../ps2dev
# (ps2dev v2.0.0 for Windows from github.com/ps2dev/ps2dev, plus the i686 MinGW
#  runtime DLLs from repo.msys2.org copied next to the gcc binaries).
# usage (Git Bash):  sh tools/elf/build.sh      -> tools/elf/PSX_LANGUAGE_TOOL.ELF
set -e
cd "$(dirname "$0")"
PS2DEV="${PS2DEV:-$(cd ../ps2dev && pwd)}"
P="$PS2DEV/ps2sdk"; T="$PS2DEV/ee/bin/mips64r5900el-ps2-elf-"; I="$P/iop/irx"; B="$P/bin/bin2c"
[ -x "$B.exe" ] && B="$B.exe"; [ -x "${T}gcc.exe" ] && X=.exe || X=
mkdir -p gen
$B "$I/iomanX.irx"     gen/irx_iomanX.c   iomanX_irx
$B "$I/fileXio.irx"    gen/irx_fileXio.c  fileXio_irx
$B "$I/poweroff.irx"   gen/irx_poweroff.c poweroff_irx
$B "$I/ps2dev9.irx"    gen/irx_dev9.c     ps2dev9_irx
$B "$I/ps2atad.irx"    gen/irx_atad.c     ps2atad_irx
$B "$I/ps2hdd-osd.irx" gen/irx_hdd.c      ps2hdd_irx
$B "$I/ps2fs.irx"      gen/irx_pfs.c      ps2fs_irx
$B "../../SYSTEM-DIC GER/jp.dic"  gen/dic_ger.c dic_ger
$B "../../SYSTEM-DIC ENG/jp.dic" gen/dic_eng.c dic_eng
$B "../../SYSTEM-DIC POL/jp.dic" gen/dic_pol.c dic_pol
$B "../../SYSTEM-DIC ESP/jp.dic" gen/dic_esp.c dic_esp
$B jp_original.dic                gen/dic_jpn.c dic_jpn
# XMB texts of all models and languages (zlib packed), checked before embedding
python pack_xmb.py ../.. gen/xmb_pack.bin
python check_pack.py ../.. gen/xmb_pack.bin
$B gen/xmb_pack.bin gen/xmb_pack.c xmb_pack
${T}gcc$X -D_EE -DNEWLIB_PORT_AWARE -G0 -O2 -Wall -I"$P/ee/include" -I"$P/common/include" -I"$P/ports/include" \
  -I"$PS2DEV/gsKit/include" gui.c gen/*.c -T"$P/ee/startup/linkfile" -L"$P/ee/lib" -L"$P/ports/lib" \
  -L"$PS2DEV/gsKit/lib" -Wl,-zmax-page-size=128 \
  -lgskit -ldmakit -lpad -lpoweroff -lfileXio -lpatches -lz -o PSX_LANGUAGE_TOOL.ELF
${T}strip$X PSX_LANGUAGE_TOOL.ELF
cp PSX_LANGUAGE_TOOL.ELF ../../ELF-INSTALLER/
echo built PSX_LANGUAGE_TOOL.ELF "(copied to ELF-INSTALLER)"
