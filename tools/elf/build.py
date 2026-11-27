"""Builds PSX_LANGUAGE_TOOL.ELF (needs the language folders from tools/build_all.py).

usage: python tools/elf/build.py      -> tools/elf/PSX_LANGUAGE_TOOL.ELF (copied to ELF-INSTALLER)

Uses the ps2dev v2.0.0 toolchain in tools/ps2dev (or $PS2DEV). If it is missing it is
downloaded from github.com/ps2dev/ps2dev (~270 MB, only ee/, ps2sdk/ and gsKit/ are
unpacked). On Windows the MinGW runtime DLLs the toolchain needs are taken from
repo.msys2.org (python package zstandard is installed into build/pydeps for that).
"""
import os, sys, io, re, glob, shutil, tarfile, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DL = os.path.join(ROOT, 'build', 'download')
WIN = sys.platform == 'win32'
REL = 'https://github.com/ps2dev/ps2dev/releases/download/v2.0.0/'
ASSET = {'win32': 'ps2dev-windows-latest.tar.gz', 'darwin': 'ps2dev-macos-latest.tar.gz'}.get(
    sys.platform, 'ps2dev-ubuntu-latest.tar.gz')
MSYS = 'https://repo.msys2.org/mingw/mingw32/'
# runtime DLLs of the Windows toolchain (i686 MinGW): package -> pinned version
DLL_PKGS = {'libgcc': '16.2.0-7', 'libiconv': '1.19.1-1', 'libwinpthread': '14.0.0.r598.ge3d18511f-1',
            'gmp': '6.3.0-2', 'mpfr': '4.2.2-3', 'mpc': '1.4.1-1', 'isl': '0.27-1', 'zstd': '1.5.7-2'}
GCC = 'ee/bin/mips64r5900el-ps2-elf-'


def download(url, name):
    os.makedirs(DL, exist_ok=True)
    out = os.path.join(DL, name)
    if not os.path.exists(out):
        print('download', url)
        with urllib.request.urlopen(url) as r, open(out + '.part', 'wb') as f:
            total, n = int(r.headers.get('Content-Length') or 0), 0
            while chunk := r.read(1 << 20):
                f.write(chunk)
                n += len(chunk)
                if total and sys.stdout.isatty():
                    print(f'\r  {n >> 20} / {total >> 20} MB', end='', flush=True)
        if sys.stdout.isatty():
            print()
        os.replace(out + '.part', out)
    return out


def zstd():
    try:
        import zstandard
    except ImportError:
        deps = os.path.join(ROOT, 'build', 'pydeps')
        if not glob.glob(os.path.join(deps, 'zstandard*')):
            print('installing python package zstandard into build/pydeps')
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--target', deps, 'zstandard'], check=True)
        sys.path.insert(0, deps)
        import zstandard
    return zstandard


def toolchain():
    ps2dev = os.environ.get('PS2DEV') or os.path.join(ROOT, 'tools', 'ps2dev')
    if os.path.exists(os.path.join(ps2dev, GCC + 'gcc' + ('.exe' if WIN else ''))):
        return ps2dev
    if os.environ.get('PS2DEV'):
        sys.exit(f'PS2DEV={ps2dev}: no ee gcc inside')
    part = ps2dev + '.part'
    shutil.rmtree(part, ignore_errors=True)
    print('unpacking toolchain into tools/ps2dev')
    keep = ('ps2dev/ee/', 'ps2dev/ps2sdk/', 'ps2dev/gsKit/')   # the archive has a top folder ps2dev/
    with tarfile.open(download(REL + ASSET, ASSET)) as t:
        t.extractall(part, members=[m for m in t if m.name.startswith(keep)],
                     **({'filter': 'tar'} if hasattr(tarfile, 'tar_filter') else {}))
    tmp = os.path.join(part, 'ps2dev')
    if WIN:
        z = zstd()
        dlls = {}
        for p, v in DLL_PKGS.items():
            f = f'mingw-w64-i686-{p}-{v}-any.pkg.tar.zst'
            data = io.BytesIO()
            with open(download(MSYS + f, f), 'rb') as fh:
                z.ZstdDecompressor().copy_stream(fh, data)
            data.seek(0)
            with tarfile.open(fileobj=data) as t:
                for m in t:
                    if m.isfile() and re.fullmatch(r'mingw32/bin/[^/]+\.dll', m.name):
                        dlls[os.path.basename(m.name)] = t.extractfile(m).read()
        # next to every program of the toolchain
        for d in {os.path.dirname(p) for p in glob.glob(os.path.join(tmp, 'ee', '**', '*.exe'), recursive=True)}:
            for n, b in dlls.items():
                open(os.path.join(d, n), 'wb').write(b)
    os.replace(tmp, ps2dev)
    shutil.rmtree(part, ignore_errors=True)
    return ps2dev


def bin2c(src, dst, name):
    """same output as ps2sdk bin2c"""
    data = open(src, 'rb').read()
    with open(dst, 'w', newline='\n') as f:
        f.write(f'#ifndef __{name}__\n#define __{name}__\n\n'
                f'unsigned int size_{name} = {len(data)};\n'
                f'unsigned char {name}[] __attribute__((aligned(16))) = {{')
        for i, b in enumerate(data):
            f.write(('\n\t' if i % 16 == 0 else '') + f'0x{b:02x}, ')
        f.write('\n};\n\n#endif\n')


def main():
    p = toolchain()
    sdk, irx = os.path.join(p, 'ps2sdk'), os.path.join(p, 'ps2sdk', 'iop', 'irx')
    os.chdir(HERE)
    os.makedirs('gen', exist_ok=True)
    for f, c, n in [('iomanX', 'iomanX', 'iomanX_irx'), ('fileXio', 'fileXio', 'fileXio_irx'),
                    ('poweroff', 'poweroff', 'poweroff_irx'), ('ps2dev9', 'dev9', 'ps2dev9_irx'),
                    ('ps2atad', 'atad', 'ps2atad_irx'), ('ps2hdd-osd', 'hdd', 'ps2hdd_irx'),
                    ('ps2fs', 'pfs', 'ps2fs_irx')]:
        bin2c(os.path.join(irx, f + '.irx'), f'gen/irx_{c}.c', n)
    for l in ('GER', 'ENG', 'POL', 'ESP'):
        src = os.path.join(ROOT, f'SYSTEM-DIC {l}', 'jp.dic')
        if not os.path.exists(src):
            sys.exit(f'missing {src} - run tools/build_all.py first')
        bin2c(src, f'gen/dic_{l.lower()}.c', f'dic_{l.lower()}')
    bin2c('jp_original.dic', 'gen/dic_jpn.c', 'dic_jpn')
    # XMB texts of all models and languages (zlib packed), checked before embedding
    for s in ('pack_xmb.py', 'check_pack.py'):
        subprocess.run([sys.executable, s, ROOT, 'gen/xmb_pack.bin'], check=True)
    bin2c('gen/xmb_pack.bin', 'gen/xmb_pack.c', 'xmb_pack')
    cc = os.path.join(p, GCC)
    env = dict(os.environ, PATH=os.path.join(p, 'ee', 'bin') + os.pathsep + os.environ.get('PATH', ''))
    subprocess.run([cc + 'gcc', '-D_EE', '-DNEWLIB_PORT_AWARE', '-G0', '-O2', '-Wall',
                    f'-I{sdk}/ee/include', f'-I{sdk}/common/include', f'-I{sdk}/ports/include',
                    f'-I{p}/gsKit/include', 'gui.c', *sorted(glob.glob('gen/*.c')),
                    f'-T{sdk}/ee/startup/linkfile', f'-L{sdk}/ee/lib', f'-L{sdk}/ports/lib',
                    f'-L{p}/gsKit/lib', '-Wl,-zmax-page-size=128',
                    '-lgskit', '-ldmakit', '-lpad', '-lpoweroff', '-lfileXio', '-lpatches', '-lz',
                    '-o', 'PSX_LANGUAGE_TOOL.ELF'], check=True, env=env)
    subprocess.run([cc + 'strip', 'PSX_LANGUAGE_TOOL.ELF'], check=True, env=env)
    shutil.copyfile('PSX_LANGUAGE_TOOL.ELF', os.path.join(ROOT, 'ELF-INSTALLER', 'PSX_LANGUAGE_TOOL.ELF'))
    print('built PSX_LANGUAGE_TOOL.ELF (copied to ELF-INSTALLER)')


if __name__ == '__main__':
    main()
