/* PSX (DESR) system dictionary installer.
 * Mounts hdd0:__system, backs up /dic/jp.dic to /dic/jp.dic.bak (only once),
 * then writes the embedded jp.dic.  Build with -DMODE_RESTORE to copy the
 * backup back instead.  Messages: -DLANG_EN for English, default German.
 */
#include <kernel.h>
#include <sifrpc.h>
#include <loadfile.h>
#include <iopcontrol.h>
#include <sbv_patches.h>
#include <fileXio_rpc.h>
#include <io_common.h>
#include <iox_stat.h>
#include <debug.h>
#include <string.h>
#include <stdlib.h>

#define IRX(n) extern unsigned char n[]; extern unsigned int size_##n;
IRX(iomanX_irx) IRX(fileXio_irx) IRX(poweroff_irx) IRX(ps2dev9_irx)
IRX(ps2atad_irx) IRX(ps2hdd_irx) IRX(ps2fs_irx)
#ifndef MODE_RESTORE
extern unsigned char dic_data[]; extern unsigned int size_dic_data;
#endif

#ifdef LANG_EN
#define T_TITLE   "PSX system dictionary - English button labels"
#define T_RTITLE  "PSX system dictionary - restore original"
#define T_MOD     "Loading driver %s ... "
#define T_MOUNT   "Mounting hdd0:__system ... "
#define T_NODIC   "Folder /dic not found - nothing changed."
#define T_BAK     "Backing up jp.dic -> jp.dic.bak ... "
#define T_BAKOK   "Backup jp.dic.bak already exists, kept."
#define T_WRITE   "Writing new jp.dic ... "
#define T_VERIFY  "Verifying ... "
#define T_NOBAK   "No jp.dic.bak found - nothing to restore."
#define T_RESTORE "Restoring jp.dic from jp.dic.bak ... "
#define T_DONE    "DONE. Please switch the PSX off and on again."
#define T_FAIL    "FAILED (%d). Please switch the PSX off and on again."
#else
#define T_TITLE   "PSX Systemwoerterbuch - deutsche Tastenhinweise"
#define T_RTITLE  "PSX Systemwoerterbuch - Original wiederherstellen"
#define T_MOD     "Lade Treiber %s ... "
#define T_MOUNT   "Binde hdd0:__system ein ... "
#define T_NODIC   "Ordner /dic nicht gefunden - nichts geaendert."
#define T_BAK     "Sichere jp.dic -> jp.dic.bak ... "
#define T_BAKOK   "Sicherung jp.dic.bak existiert schon, bleibt erhalten."
#define T_WRITE   "Schreibe neue jp.dic ... "
#define T_VERIFY  "Pruefe ... "
#define T_NOBAK   "Keine jp.dic.bak gefunden - nichts wiederherzustellen."
#define T_RESTORE "Stelle jp.dic aus jp.dic.bak wieder her ... "
#define T_DONE    "FERTIG. Bitte den PSX aus- und wieder einschalten."
#define T_FAIL    "FEHLER (%d). Bitte den PSX aus- und wieder einschalten."
#endif

#define DIC  "pfs0:/dic/jp.dic"
#define BAK  "pfs0:/dic/jp.dic.bak"

static int load(const char *name, unsigned char *buf, unsigned int size,
                const char *args, int arglen)
{
    int ret = 0, id;
    scr_printf(T_MOD, name);
    id = SifExecModuleBuffer(buf, size, arglen, args, &ret);
    if (id < 0 || ret == 1) {
        scr_printf("ERR %d/%d\n", id, ret);
        return -1;
    }
    scr_printf("OK\n");
    return 0;
}

static int file_size(const char *path)
{
    iox_stat_t st;
    if (fileXioGetStat(path, &st) < 0)
        return -1;
    return (int)st.size;
}

static int read_file(const char *path, unsigned char **out)
{
    int fd, n = file_size(path), r;
    if (n < 0)
        return -1;
    *out = malloc(n + 1);
    if (!*out)
        return -2;
    fd = fileXioOpen(path, FIO_O_RDONLY);
    if (fd < 0)
        return fd;
    r = fileXioRead(fd, *out, n);
    fileXioClose(fd);
    return r == n ? n : -3;
}

static int write_file(const char *path, const unsigned char *buf, int n)
{
    int fd = fileXioOpen(path, FIO_O_WRONLY | FIO_O_CREAT | FIO_O_TRUNC, 0666);
    int w;
    if (fd < 0)
        return fd;
    w = fileXioWrite(fd, buf, n);
    fileXioClose(fd);
    return w == n ? 0 : -4;
}

/* write, then read back and compare */
static int write_checked(const char *path, const unsigned char *buf, int n)
{
    unsigned char *chk = NULL;
    int r = write_file(path, buf, n);
    if (r < 0)
        return r;
    scr_printf("OK\n" T_VERIFY);
    r = read_file(path, &chk);
    if (r != n || memcmp(chk, buf, n) != 0)
        r = -5;
    else
        r = 0;
    free(chk);
    return r;
}

static void finish(int err)
{
    fileXioUmount("pfs0:");
    if (err)
        scr_printf("\n" T_FAIL "\n", err);
    else
        scr_printf("OK\n\n" T_DONE "\n");
    SleepThread();
}

int main(int argc, char *argv[])
{
    static const char hdd_args[] = "-o\0" "4\0" "-n\0" "20";
    static const char pfs_args[] = "-m\0" "4\0" "-o\0" "10\0" "-n\0" "40";
    int r;

    init_scr();
#ifdef MODE_RESTORE
    scr_printf("\n  " T_RTITLE "\n\n");
#else
    scr_printf("\n  " T_TITLE "\n\n");
#endif

    SifInitRpc(0);
    while (!SifIopReset("", 0)) {}
    while (!SifIopSync()) {}
    SifInitRpc(0);
    SifLoadFileInit();
    sbv_patch_enable_lmb();
    sbv_patch_disable_prefix_check();

    if (load("iomanX", iomanX_irx, size_iomanX_irx, NULL, 0) ||
        load("fileXio", fileXio_irx, size_fileXio_irx, NULL, 0) ||
        load("poweroff", poweroff_irx, size_poweroff_irx, NULL, 0) ||
        load("dev9", ps2dev9_irx, size_ps2dev9_irx, NULL, 0) ||
        load("atad", ps2atad_irx, size_ps2atad_irx, NULL, 0) ||
        load("hdd", ps2hdd_irx, size_ps2hdd_irx, hdd_args, sizeof(hdd_args)) ||
        load("pfs", ps2fs_irx, size_ps2fs_irx, pfs_args, sizeof(pfs_args))) {
        scr_printf("\n" T_FAIL "\n", 1);
        SleepThread();
    }
    fileXioInit();

    scr_printf(T_MOUNT);
    r = fileXioMount("pfs0:", "hdd0:__system", FIO_MT_RDWR);
    if (r < 0) {
        scr_printf("\n" T_FAIL "\n", r);
        SleepThread();
    }
    scr_printf("OK\n");

    {
        iox_stat_t st;
        if (fileXioGetStat("pfs0:/dic", &st) < 0 || !FIO_S_ISDIR(st.mode)) {
            scr_printf(T_NODIC "\n");
            finish(2);
        }
    }

#ifdef MODE_RESTORE
    {
        unsigned char *b = NULL;
        int n = read_file(BAK, &b);
        if (n < 0) {
            scr_printf(T_NOBAK "\n");
            finish(3);
        }
        scr_printf(T_RESTORE);
        r = write_checked(DIC, b, n);
        free(b);
        finish(r);
    }
#else
    if (file_size(BAK) >= 0) {
        scr_printf(T_BAKOK "\n");
    } else if (file_size(DIC) >= 0) {
        unsigned char *b = NULL;
        int n = read_file(DIC, &b);
        scr_printf(T_BAK);
        if (n < 0) {
            finish(n);
        }
        r = write_checked(BAK, b, n);
        free(b);
        if (r < 0)
            finish(r);
        scr_printf("OK\n");
    }
    scr_printf(T_WRITE);
    r = write_checked(DIC, dic_data, size_dic_data);
    finish(r);
#endif
    return 0;
}
