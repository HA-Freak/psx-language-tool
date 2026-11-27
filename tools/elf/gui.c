/* PSX Language Tool - installs German / English / Polish / Spanish on the PSX (DESR)
 *
 * Recognises the model series by the hdd0:__system partition:
 *   DESR-5500/5700/7500/7700  (has /dic)  -> XMB texts + button labels (dic/jp.dic)
 *   DESR-5000/5100/7000/7100  (no  /dic)  -> XMB texts
 *
 * The XMB files of all languages are built into this ELF (gen/xmb_pack.bin,
 * zlib compressed, see pack_xmb.py). Before the first install every file that
 * will be overwritten is copied to hdd0:__system/langtool_bak/ together with a
 * manifest (files that did not exist are listed and removed on restore).
 * That backup is never overwritten, so "Restore backup" always returns to the
 * state before the first install. jp.dic is additionally saved as jp.dic.bak.
 *
 * Controls: D-pad up/down, X or O = choose, START = confirm, other = cancel.
 */
#include <kernel.h>
#include <sifrpc.h>
#include <loadfile.h>
#include <iopcontrol.h>
#include <sbv_patches.h>
#include <fileXio_rpc.h>
#include <io_common.h>
#include <iox_stat.h>
#include <libpad.h>
#include <libpwroff.h>
#include <gsKit.h>
#include <dmaKit.h>
#include <zlib.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>
#include "font.h"   /* anti-aliased 10x18 font, see gen_font.ps1 */

#define IRX(n) extern unsigned char n[]; extern unsigned int size_##n;
IRX(iomanX_irx) IRX(fileXio_irx) IRX(poweroff_irx) IRX(ps2dev9_irx)
IRX(ps2atad_irx) IRX(ps2hdd_irx) IRX(ps2fs_irx)
IRX(dic_ger) IRX(dic_eng) IRX(dic_pol) IRX(dic_esp) IRX(dic_jpn)
IRX(xmb_pack)

#define DIC      "pfs0:/dic/jp.dic"
#define BAK      "pfs0:/dic/jp.dic.bak"
#define BKDIR    "pfs0:/langtool_bak/"
#define MANIFEST BKDIR "manifest.txt"

/* colours are 0x00BBGGRR */
#define C_BG     0x00301800
#define C_BAR    0x00603010
#define C_SEL    0x00704020
#define C_BOX    0x00402008
#define C_WHITE  0x00ffffff
#define C_GRAY   0x00a0a0a0
#define C_YELLOW 0x0000ffff
#define C_GREEN  0x0040ff40
#define C_RED    0x004040ff
#define C_CYAN   0x00ffff00

static char padBuf[256] __attribute__((aligned(64)));
static int hdd_ok = 0, pad_ok = 0;
static int series = -1;                 /* 0 = DESR-5000 series, 1 = DESR-5500 series */
static char fw[16] = "?";
static char st_hdd[64], st_model[72], st_xmb[72], st_dic[72], st_bak[72];
static char msg[4][72], prog[72];       /* prog = progress line, separate from the log */
static u32 msgcol[4];
static int asking = -1;                 /* action waiting for START, or -1 */

static const char *SERIES_NAME[2] = { "DESR-5000/5100/7000/7100", "DESR-5500/5700/7500/7700" };
static const char *SERIES_FW[2]   = { "1.31", "2.11" };
#define NLANG 4
static const char *LANG_NAME[NLANG] = { "German", "English", "Polish", "Spanish" };

enum { A_GER, A_ENG, A_POL, A_ESP, A_RESTORE, A_JPN, A_MKBAK, A_STATUS, A_OFF };
static int menu[A_OFF + 1], nmenu, sel;

/* ---------- helpers ---------- */
static void wait_ms(int ms)
{
    volatile int i;
    while (ms-- > 0)
        for (i = 0; i < 30000; i++) {}
}

static void log_msg(u32 col, const char *fmt, ...)
{
    va_list ap;
    int i;
    for (i = 0; i < 3; i++) {
        strcpy(msg[i], msg[i + 1]);
        msgcol[i] = msgcol[i + 1];
    }
    va_start(ap, fmt);
    vsnprintf(msg[3], sizeof(msg[3]), fmt, ap);
    va_end(ap);
    msgcol[3] = col;
}

static int file_size(const char *path)
{
    iox_stat_t st;
    if (fileXioGetStat(path, &st) < 0)
        return -1;
    return (int)st.size;
}

static int is_dir(const char *path)
{
    iox_stat_t st;
    return fileXioGetStat(path, &st) >= 0 && FIO_S_ISDIR(st.mode);
}

static int read_file(const char *path, unsigned char **out)
{
    int fd, n = file_size(path), r;
    *out = NULL;
    if (n < 0)
        return -1;
    *out = malloc(n + 1);
    if (!*out)
        return -2;
    fd = fileXioOpen(path, FIO_O_RDONLY);
    if (fd < 0) {
        free(*out);
        *out = NULL;
        return fd;
    }
    r = n ? fileXioRead(fd, *out, n) : 0;
    fileXioClose(fd);
    (*out)[n] = 0;
    if (r != n) {
        free(*out);
        *out = NULL;
        return -3;
    }
    return n;
}

static int write_file(const char *path, const unsigned char *buf, int n)
{
    int fd = fileXioOpen(path, FIO_O_WRONLY | FIO_O_CREAT | FIO_O_TRUNC, 0666), w;
    if (fd < 0)
        return fd;
    w = n ? fileXioWrite(fd, buf, n) : 0;
    fileXioClose(fd);
    return w == n ? 0 : -4;
}

static int same_file(const char *path, const unsigned char *buf, int n)
{
    unsigned char *b;
    int r = read_file(path, &b), ok = (r == n && memcmp(b, buf, n) == 0);
    free(b);
    return ok;
}

/* create every directory of "pfs0:/a/b/file" (errors for existing ones are ignored) */
static void mkdirs(const char *path)
{
    char tmp[256];
    char *p;
    strncpy(tmp, path, sizeof(tmp) - 1);
    tmp[sizeof(tmp) - 1] = 0;
    for (p = tmp + 6; (p = strchr(p, '/')) != NULL; p++) {
        *p = 0;
        fileXioMkdir(tmp, 0777);
        *p = '/';
    }
}

/* unmount + remount so PFS/HDD caches are definitely written to disk */
static void flush_disk(void)
{
    fileXioUmount("pfs0:");
    if (fileXioMount("pfs0:", "hdd0:__system", FIO_MT_RDWR) < 0)
        hdd_ok = 0;
}

static int write_checked(const char *path, const unsigned char *buf, int n)
{
    int r = write_file(path, buf, n);
    if (r < 0)
        return r;
    flush_disk();
    return same_file(path, buf, n) ? 0 : -5;
}

/* ---------- built-in XMB pack ---------- */
typedef struct { u32 series, lang, n, first, probe; } pkset;

static u32 rd32(const unsigned char *p)
{
    return p[0] | (p[1] << 8) | (p[2] << 16) | ((u32)p[3] << 24);
}
static u32 H(int i) { return rd32(xmb_pack + 4 + 4 * i); }   /* header fields */

static const char *pk_path(u32 i)
{
    return (const char *)xmb_pack + H(4) + rd32(xmb_pack + H(4) + 4 * i);
}

static void pk_file(const pkset *s, u32 j, u32 *path, u32 *blob)
{
    const unsigned char *p = xmb_pack + H(6) + 8 * (s->first + j);
    *path = rd32(p);
    *blob = rd32(p + 4);
}

static unsigned char *pk_blob(u32 i, int *len)
{
    const unsigned char *b = xmb_pack + H(3) + 12 * i;
    u32 off = rd32(b), cs = rd32(b + 4), rs = rd32(b + 8);
    uLongf dl = rs;
    unsigned char *out = malloc(rs + 1);
    if (!out)
        return NULL;
    if (uncompress(out, &dl, xmb_pack + H(7) + off, cs) != Z_OK || dl != rs) {
        free(out);
        return NULL;
    }
    *len = (int)rs;
    return out;
}

static int pk_find(int ser, int lang, pkset *s)
{
    u32 k;
    if (memcmp(xmb_pack, "PXMB", 4) != 0)
        return -1;
    for (k = 0; k < H(0); k++) {
        const unsigned char *p = xmb_pack + H(5) + 20 * k;
        if ((int)rd32(p) == ser && (int)rd32(p + 4) == lang) {
            s->series = rd32(p);
            s->lang = rd32(p + 4);
            s->n = rd32(p + 8);
            s->first = rd32(p + 12);
            s->probe = rd32(p + 16);
            return 0;
        }
    }
    return -1;
}

/* ---------- status ---------- */
static const char *dic_lang(const unsigned char *b)
{
    if (strstr((const char *)b, "\xe6\x88\xbb\xe3\x82\x8b"))   /* modoru */
        return "Japanese (original)";
    if (strstr((const char *)b, "Zur\xc3\xbc" "ck"))
        return "German";
    if (strstr((const char *)b, "\"Control Panel\""))
        return "English";
    if (strstr((const char *)b, "\"Panel sterowania\""))
        return "Polish";
    if (strstr((const char *)b, "\"Panel de control\""))
        return "Spanish";
    return "unknown";
}

static int dic_is_japanese(void)
{
    unsigned char *b;
    int r = 0;
    if (read_file(DIC, &b) >= 0) {
        r = strstr((char *)b, "\xe6\x88\xbb\xe3\x82\x8b") != NULL;
        free(b);
    }
    return r;
}

static const char *xmb_lang(void)
{
    pkset s;
    char path[256];
    unsigned char *disk, *ref;
    int n, len, l;
    const char *res = "other (original or older mod)";
    if (pk_find(series, 1, &s) < 0)
        return "?";
    snprintf(path, sizeof(path), "pfs0:/%s", pk_path(s.probe));
    n = read_file(path, &disk);
    if (n < 0)
        return "probe file missing";
    for (l = 0; l < NLANG; l++) {
        pkset t;
        u32 j, pi, bi;
        if (pk_find(series, l, &t) < 0)
            continue;
        for (j = 0; j < t.n; j++) {
            pk_file(&t, j, &pi, &bi);
            if (pi == t.probe)
                break;
        }
        if (j == t.n || !(ref = pk_blob(bi, &len)))
            continue;
        if (len == n && memcmp(ref, disk, n) == 0)
            res = LANG_NAME[l];
        free(ref);
    }
    free(disk);
    return res;
}

static void read_status(void)
{
    unsigned char *b;
    int n;
    st_model[0] = st_xmb[0] = st_dic[0] = st_bak[0] = 0;
    if (!hdd_ok)
        return;
    if (series < 0)
        snprintf(st_model, sizeof(st_model), "unknown (firmware %s) - not supported", fw);
    else
        snprintf(st_model, sizeof(st_model), "%s, firmware %s", SERIES_NAME[series], fw);
    if (series < 0)
        return;
    snprintf(st_xmb, sizeof(st_xmb), "%s", xmb_lang());
    if (series == 1) {
        n = read_file(DIC, &b);
        if (n < 0)
            strcpy(st_dic, "missing!");
        else {
            snprintf(st_dic, sizeof(st_dic), "%s", dic_lang(b));
            free(b);
        }
    }
    snprintf(st_bak, sizeof(st_bak), "XMB %s%s",
             file_size(MANIFEST) >= 0 ? "yes" : "no",
             series == 1 ? (file_size(BAK) >= 0 ? ", jp.dic.bak yes" : ", jp.dic.bak no") : "");
}

/* ---------- screen ----------
 * Everything is drawn into a 32-bit canvas with an anti-aliased 10x18 font,
 * passed through a 1-2-1 vertical flicker filter (interlaced TV output) and
 * shown as one texture. A ~5 % border keeps the text inside the TV overscan.
 * Layout (rows of LH pixels): 0 title bar, 2-6 status, 8-15 menu, 16 help,
 * 18-20 messages, 21 progress, 22 button legend; confirm box over rows 17-20.                          */
#define SW_MAX 640
#define SH_MAX 512
#define LH     16
#define ROWS   23
static GSGLOBAL *gs;
static GSTEXTURE tex;
static u32 canvas[SW_MAX * SH_MAX] __attribute__((aligned(128)));
static u32 texbuf[SW_MAX * SH_MAX] __attribute__((aligned(128)));
static int SW = 640, SH = 448, X0 = 32, Y0 = 28;

static void gfx_init(void)
{
    dmaKit_init(D_CTRL_RELE_OFF, D_CTRL_MFD_OFF, D_CTRL_STS_UNSPEC, D_CTRL_STD_OFF,
                D_CTRL_RCYC_8, 1 << DMA_CHANNEL_GIF);
    dmaKit_chan_init(DMA_CHANNEL_GIF);
    gs = gsKit_init_global();
    gs->PSM = GS_PSM_CT32;
    gs->ZBuffering = GS_SETTING_OFF;
    gs->DoubleBuffering = GS_SETTING_OFF;
    gs->PrimAlphaEnable = GS_SETTING_OFF;
    gsKit_init_screen(gs);
    gsKit_mode_switch(gs, GS_ONESHOT);
    SW = gs->Width < SW_MAX ? gs->Width : SW_MAX;
    SH = gs->Height < SH_MAX ? gs->Height : SH_MAX;
    X0 = SW / 20;
    Y0 = (SH - ROWS * LH) / 2;
    memset(&tex, 0, sizeof(tex));
    tex.Width = SW;
    tex.Height = SH;
    tex.PSM = GS_PSM_CT32;
    tex.Mem = texbuf;
    tex.Filter = GS_FILTER_NEAREST;
    tex.Vram = gsKit_vram_alloc(gs, gsKit_texture_size(SW, SH, GS_PSM_CT32), GSKIT_ALLOC_USERBUFFER);
}

static void fill(int x, int y, int w, int h, u32 c)
{
    int i, j;
    if (x < 0) { w += x; x = 0; }
    if (y < 0) { h += y; y = 0; }
    if (x + w > SW) w = SW - x;
    if (y + h > SH) h = SH - y;
    for (j = 0; j < h; j++)
        for (i = 0; i < w; i++)
            canvas[(y + j) * SW + x + i] = c;
}

/* draws s at pixel x / text row r, clipped at the right border; returns the new x */
static int yoff;                             /* pixel shift for a block of rows */

static int text(int x, int r, u32 col, const char *s)
{
    int y = Y0 + r * LH + yoff, gx, gy;
    for (; *s && x + FONT_W <= SW - X0 / 2; s++, x += FONT_W) {
        unsigned char ch = (unsigned char)*s > 126 ? '?' : (unsigned char)*s;
        const unsigned char *g = font_glyph[ch];
        for (gy = 0; gy < FONT_H; gy++) {
            u32 *p = canvas + (y + gy) * SW + x;
            if (y + gy < 0 || y + gy >= SH)
                continue;
            for (gx = 0; gx < FONT_W; gx++) {
                int a = g[gy * FONT_W + gx], k;
                u32 d = p[gx], o = 0;
                if (!a)
                    continue;
                for (k = 0; k < 24; k += 8) {
                    int dc = (d >> k) & 0xff, cc = (col >> k) & 0xff;
                    o |= (u32)(dc + (cc - dc) * a / 15) << k;
                }
                p[gx] = o;
            }
        }
    }
    return x;
}

static int textf(int x, int r, u32 col, const char *fmt, ...)
{
    char buf[128];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    return text(x, r, col, buf);
}

static void present(void)
{
    int x, y;
    for (y = 0; y < SH; y++) {
        const u32 *a = canvas + (y ? y - 1 : 0) * SW, *b = canvas + y * SW;
        const u32 *c = canvas + (y + 1 < SH ? y + 1 : y) * SW;
        u32 *o = texbuf + y * SW;
        for (x = 0; x < SW; x++) {
            u32 lo = (((a[x] & 0xff00ff) + 2 * (b[x] & 0xff00ff) + (c[x] & 0xff00ff)) >> 2) & 0xff00ff;
            u32 hi = ((((a[x] >> 8) & 0xff) + 2 * ((b[x] >> 8) & 0xff) + ((c[x] >> 8) & 0xff)) >> 2) & 0xff;
            o[x] = 0x80000000 | lo | (hi << 8);
        }
    }
    FlushCache(0);
    gsKit_texture_upload(gs, &tex);
    gsKit_prim_sprite_texture(gs, &tex, 0, 0, 0, 0, SW, SH, SW, SH, 0,
                              GS_SETREG_RGBAQ(0x80, 0x80, 0x80, 0x80, 0x00));
    gsKit_queue_exec(gs);
    gsKit_sync_flip(gs);
}

static const char *item_text(int a)
{
    switch (a) {
    case A_GER:     return "Install German";
    case A_ENG:     return "Install English";
    case A_POL:     return "Install Polish";
    case A_ESP:     return "Install Spanish";
    case A_RESTORE: return "Restore backup (state before first install)";
    case A_JPN:     return "Restore Japanese button labels only";
    case A_MKBAK:   return "Create backup now";
    case A_STATUS:  return "Refresh status";
    default:        return "Power off PSX";
    }
}

static const char *item_help(int a)
{
    switch (a) {
    case A_GER: case A_ENG: case A_POL: case A_ESP:
        return series == 1 ? "XMB menus and dialogs + button labels (jp.dic)."
                           : "XMB menus and dialogs (xosd packages).";
    case A_RESTORE: return "Puts back the files saved in langtool_bak.";
    case A_JPN:     return "Writes the original Sony jp.dic (built in).";
    case A_MKBAK:   return "Saves the current files (only if no backup yet).";
    case A_STATUS:  return "Checks hard disk, language and backup again.";
    default:        return "Unmounts the hard disk and powers off.";
    }
}

static void status_row(int r, const char *label, u32 col, const char *val)
{
    text(text(X0, r, C_GRAY, label), r, col, val);
}

static void draw(void)
{
    int i, x, r, by, m0;
    fill(0, 0, SW, SH, C_BG);

    fill(0, Y0 - 5, SW, LH + 8, C_BAR);
    text(X0, 0, C_WHITE, "PSX Language Tool");
    text(SW - X0 - 35 * FONT_W, 0, C_CYAN, "German / English / Polish / Spanish");

    yoff = -6;                               /* status a bit up, menu a bit down: */
    r = 2;                                   /* 9 menu items fit below 5 status rows */
    status_row(r++, "Hard disk  ", hdd_ok ? C_GREEN : C_RED, st_hdd);
    if (hdd_ok) {
        status_row(r++, "Model      ", series < 0 ? C_RED : C_WHITE, st_model);
        if (series >= 0) {
            status_row(r++, "XMB        ", C_WHITE, st_xmb);
            if (series == 1)
                status_row(r++, "jp.dic     ", C_WHITE, st_dic);
            status_row(r++, "Backup     ", C_WHITE, st_bak);
        }
    }

    yoff = 3;
    m0 = 16 - nmenu;                         /* menu ends at row 15, help in row 16 */
    for (i = 0; i < nmenu; i++) {
        if (i == sel) {
            fill(X0 - 8, Y0 + (m0 + i) * LH + yoff, SW - 2 * X0 + 16, LH, C_SEL);
            textf(X0, m0 + i, C_YELLOW, "> %d  %s", i + 1, item_text(menu[i]));
        } else
            textf(X0, m0 + i, C_WHITE, "  %d  %s", i + 1, item_text(menu[i]));
    }
    if (asking < 0)
        text(X0 + 5 * FONT_W, 16, C_GRAY, item_help(menu[sel]));
    yoff = 0;

    fill(X0, Y0 + 18 * LH - 5, SW - 2 * X0, 2, C_BAR);
    for (i = 1; i < 4; i++)
        text(X0, 17 + i, msgcol[i], msg[i]);
    text(X0, 21, C_YELLOW, prog);

    if (asking >= 0) {                       /* confirmation box over the messages */
        by = Y0 + 16 * LH + 5;
        fill(X0 - 10, by - 2, SW - 2 * X0 + 20, 5 * LH + 4, C_YELLOW);
        fill(X0 - 8, by, SW - 2 * X0 + 16, 5 * LH, C_BOX);
        textf(X0, 17, C_YELLOW, "%s ?", item_text(asking));
        text(X0, 18, C_WHITE, item_help(asking));
        if (asking <= A_ESP && series >= 0 && strcmp(fw, SERIES_FW[series]) != 0)
            textf(X0, 19, C_RED, "Warning: texts are for firmware %s, this PSX has %s.",
                  SERIES_FW[series], fw);
        x = text(X0, 20, C_WHITE, "Press ");
        x = text(x, 20, C_GREEN, "START");
        text(x, 20, C_WHITE, " to confirm, any other button to cancel.");
    }

    fill(0, Y0 + 22 * LH, SW, LH + 4, C_BAR);
    if (asking >= 0) {
        x = text(X0, 22, C_GREEN, "START");
        x = text(x, 22, C_WHITE, " confirm      ");
        text(x, 22, C_WHITE, "other button  cancel");
    } else if (prog[0]) {
        text(X0, 22, C_YELLOW, "Please wait - do not switch off the PSX.");
    } else if (!pad_ok) {
        text(X0, 22, C_RED, "No controller found in port 1!");
    } else {
        x = text(X0, 22, C_WHITE, "\x03");
        x = text(x, 22, C_WHITE, " select       ");
        x = text(x, 22, 0x00ffb060, "\x01");          /* cross: light blue */
        x = text(x, 22, C_WHITE, " / ");
        x = text(x, 22, 0x006060ff, "\x02");          /* circle: red */
        text(x, 22, C_WHITE, " run");
    }
    present();
}

static void progress(const char *what, u32 j, u32 n)
{
    if (j % 10 && j + 1 != n)
        return;
    snprintf(prog, sizeof(prog), "%s %u / %u ...", what, j + 1, n);
    draw();
}

/* ---------- pad ---------- */
static u32 old_btn = 0;

static u32 pad_pressed(void)
{
    struct padButtonStatus b;
    u32 now, edge;
    int st = padGetState(0, 0);
    if (st != PAD_STATE_STABLE && st != PAD_STATE_FINDCTP1)
        return 0;
    if (padRead(0, 0, &b) == 0)
        return 0;
    now = 0xffff ^ b.btns;
    edge = now & ~old_btn;
    old_btn = now;
    return edge;
}

static u32 wait_key(void)
{
    u32 k;
    while (!(k = pad_pressed()))
        wait_ms(16);
    return k;
}

static int confirm(int a)
{
    int r;
    asking = a;
    draw();
    r = wait_key() & PAD_START;
    asking = -1;
    return r;
}

/* ---------- backup ---------- */
static int ensure_dic_backup(void)
{
    unsigned char *b;
    int n, r;
    if (file_size(BAK) >= 0)
        return 0;
    if (!dic_is_japanese()) {
        log_msg(C_YELLOW, "Note: jp.dic is not the original - no jp.dic.bak made.");
        return 0;
    }
    n = read_file(DIC, &b);
    if (n < 0) {
        log_msg(C_RED, "Reading jp.dic failed (%d).", n);
        return n;
    }
    r = write_checked(BAK, b, n);
    free(b);
    if (r < 0)
        log_msg(C_RED, "jp.dic backup failed (%d) - aborted.", r);
    else
        log_msg(C_GREEN, "Original jp.dic saved as jp.dic.bak.");
    return r;
}

/* copies every file the pack would overwrite into langtool_bak/ (once) */
static int ensure_xmb_backup(void)
{
    pkset s;
    char src[256], dst[256];
    char *man, *state;
    unsigned char *b;
    u32 j, pi, bi;
    int n, pos = 0, saved = 0, r = 0;

    if (file_size(MANIFEST) >= 0)
        return 0;
    if (pk_find(series, 1, &s) < 0) {
        log_msg(C_RED, "Built-in data missing for this model.");
        return -1;
    }
    man = malloc(s.n * 160 + 128);
    state = malloc(s.n);
    if (!man || !state) {
        free(man);
        free(state);
        log_msg(C_RED, "Out of memory.");
        return -1;
    }
    pos = sprintf(man, "PSX Language Tool backup, %s, firmware %s\n", SERIES_NAME[series], fw);
    for (j = 0; j < s.n && r == 0; j++) {
        pk_file(&s, j, &pi, &bi);
        snprintf(src, sizeof(src), "pfs0:/%s", pk_path(pi));
        snprintf(dst, sizeof(dst), BKDIR "%s", pk_path(pi));
        n = read_file(src, &b);
        if (n >= 0) {
            mkdirs(dst);
            r = write_file(dst, b, n);
            free(b);
            state[j] = 'E';
            saved++;
        } else
            state[j] = 'N';
        pos += sprintf(man + pos, "%c %s\n", state[j], pk_path(pi));
        progress("Backup", j, s.n);
    }
    if (r == 0) {
        flush_disk();
        for (j = 0; j < s.n && r == 0 && hdd_ok; j++) {
            if (state[j] != 'E')
                continue;
            pk_file(&s, j, &pi, &bi);
            snprintf(src, sizeof(src), "pfs0:/%s", pk_path(pi));
            snprintf(dst, sizeof(dst), BKDIR "%s", pk_path(pi));
            n = read_file(src, &b);
            if (n < 0 || !same_file(dst, b, n))
                r = -5;
            free(b);
            progress("Checking backup", j, s.n);
        }
    }
    if (r == 0 && hdd_ok)
        r = write_checked(MANIFEST, (unsigned char *)man, pos);   /* written last = backup complete */
    free(man);
    free(state);
    if (r < 0 || !hdd_ok) {
        log_msg(C_RED, "XMB backup failed (%d) - nothing installed.", r);
        return -1;
    }
    log_msg(C_GREEN, "Backup: %d files saved to __system/langtool_bak.", saved);
    return 0;
}

/* ---------- actions ---------- */
static void install(int lang)
{
    static unsigned char *dics[NLANG] = { dic_ger, dic_eng, dic_pol, dic_esp };
    static unsigned int *dsize[NLANG] = { &size_dic_ger, &size_dic_eng, &size_dic_pol, &size_dic_esp };
    pkset s;
    char path[256];
    unsigned char *b;
    u32 j, pi, bi;
    int len, err = 0, r;

    if (pk_find(series, lang, &s) < 0) {
        log_msg(C_RED, "Built-in data missing for this model.");
        return;
    }
    if (ensure_xmb_backup() < 0)
        return;
    if (series == 1 && ensure_dic_backup() < 0)
        return;
    for (j = 0; j < s.n; j++) {
        pk_file(&s, j, &pi, &bi);
        snprintf(path, sizeof(path), "pfs0:/%s", pk_path(pi));
        if (!(b = pk_blob(bi, &len))) {
            err++;
            continue;
        }
        mkdirs(path);
        if (write_file(path, b, len) < 0)
            err++;
        free(b);
        progress("Installing", j, s.n);
    }
    flush_disk();
    if (!hdd_ok) {
        log_msg(C_RED, "Hard disk lost after writing!");
        return;
    }
    for (j = 0; j < s.n; j++) {
        pk_file(&s, j, &pi, &bi);
        snprintf(path, sizeof(path), "pfs0:/%s", pk_path(pi));
        if ((b = pk_blob(bi, &len)) != NULL) {
            if (!same_file(path, b, len))
                err++;
            free(b);
        }
        progress("Verifying", j, s.n);
    }
    if (series == 1) {
        r = write_checked(DIC, dics[lang], *dsize[lang]);
        if (r < 0) {
            log_msg(C_RED, "jp.dic: error %d.", r);
            err++;
        }
    }
    if (err)
        log_msg(C_RED, "%s: %d ERRORS - use 'Restore backup'.", LANG_NAME[lang], err);
    else
        log_msg(C_GREEN, "%s installed (%u files). Please restart the PSX.", LANG_NAME[lang], s.n);
}

static void restore(void)
{
    char *man, *p, *nl;
    char src[256], dst[256];
    unsigned char *b;
    int n, err = 0, done = 0, total = 0, pass;

    n = read_file(MANIFEST, (unsigned char **)&man);
    if (n < 0) {
        log_msg(C_RED, "No XMB backup present (langtool_bak/manifest.txt).");
    } else {
        for (p = man; *p; p++)
            total += *p == '\n';
        /* pass 0: write files back, pass 1: verify after flushing */
        for (pass = 0; pass < 2 && hdd_ok; pass++) {
            int j = 0;
            for (p = strchr(man, '\n'); p && p[1]; p = nl) {
                char kind = p[1];
                char *rel = p + 3;
                nl = strchr(rel, '\n');
                if (!nl)
                    break;
                *nl = 0;
                snprintf(dst, sizeof(dst), "pfs0:/%s", rel);
                snprintf(src, sizeof(src), BKDIR "%s", rel);
                if (kind == 'E') {
                    int m = read_file(src, &b);
                    if (m < 0)
                        err++;
                    else if (pass == 0) {
                        mkdirs(dst);
                        if (write_file(dst, b, m) < 0)
                            err++;
                        else
                            done++;
                    } else if (!same_file(dst, b, m))
                        err++;
                    free(b);
                } else if (kind == 'N') {
                    if (pass == 0)
                        fileXioRemove(dst);
                    else if (file_size(dst) >= 0)
                        err++;
                }
                *nl = '\n';
                progress(pass ? "Verifying" : "Restoring", j++, total - 1);
            }
            if (pass == 0)
                flush_disk();
        }
        free(man);
        if (err)
            log_msg(C_RED, "XMB restore: %d ERRORS.", err);
        else
            log_msg(C_GREEN, "XMB restored (%d files). Please restart the PSX.", done);
    }
    if (series == 1 && hdd_ok) {
        n = read_file(BAK, &b);
        if (n >= 0) {
            if (write_checked(DIC, b, n) < 0)
                log_msg(C_RED, "jp.dic restore failed.");
            else
                log_msg(C_GREEN, "jp.dic restored from jp.dic.bak.");
            free(b);
        }
    }
}

static void make_backup(void)
{
    if (file_size(MANIFEST) >= 0)
        log_msg(C_YELLOW, "XMB backup already exists - not overwritten.");
    else
        ensure_xmb_backup();
    if (series == 1) {
        if (file_size(BAK) >= 0)
            log_msg(C_YELLOW, "jp.dic.bak already exists - not overwritten.");
        else
            ensure_dic_backup();
    }
}

static void shutdown_psx(void)
{
    if (hdd_ok)
        fileXioUmount("pfs0:");
    hdd_ok = 0;
    strcpy(prog, "Powering off ...");
    draw();
    wait_ms(500);
    poweroffShutdown();
    SleepThread();
}

/* ---------- startup ---------- */
static int load(const char *name, unsigned char *buf, unsigned int size,
                const char *args, int arglen)
{
    int ret = 0, id = SifExecModuleBuffer(buf, size, arglen, args, &ret);
    if (id < 0 || ret == 1) {
        log_msg(C_RED, "Driver %s: error %d/%d", name, id, ret);
        return -1;
    }
    return 0;
}

static void detect_model(void)
{
    unsigned char *b;
    int i;
    if (read_file("pfs0:/version.txt", &b) >= 0) {
        for (i = 0; i < (int)sizeof(fw) - 1 && b[i] > ' '; i++)
            fw[i] = b[i];
        fw[i] = 0;
        free(b);
    }
    if (is_dir("pfs0:/dic") && is_dir("pfs0:/xosd/packages/AboutPSX_0"))
        series = 1;
    else if (!is_dir("pfs0:/dic") && is_dir("pfs0:/xosd/packages/Config_0"))
        series = 0;
}

static void build_menu(void)
{
    nmenu = 0;
    if (hdd_ok && series >= 0) {
        menu[nmenu++] = A_GER;
        menu[nmenu++] = A_ENG;
        menu[nmenu++] = A_POL;
        menu[nmenu++] = A_ESP;
        menu[nmenu++] = A_RESTORE;
        if (series == 1)
            menu[nmenu++] = A_JPN;
        menu[nmenu++] = A_MKBAK;
    }
    if (hdd_ok)
        menu[nmenu++] = A_STATUS;
    menu[nmenu++] = A_OFF;
    if (sel >= nmenu)
        sel = nmenu - 1;
}

static void init_all(void)
{
    static const char hdd_args[] = "-o\0" "4\0" "-n\0" "20";
    static const char pfs_args[] = "-m\0" "4\0" "-o\0" "10\0" "-n\0" "40";
    int r, i;

    SifInitRpc(0);
    while (!SifIopReset("", 0)) {}
    while (!SifIopSync()) {}
    SifInitRpc(0);
    SifLoadFileInit();
    sbv_patch_enable_lmb();
    sbv_patch_disable_prefix_check();

    strcpy(st_hdd, "Error loading drivers");
    r = load("iomanX", iomanX_irx, size_iomanX_irx, NULL, 0) ||
        load("fileXio", fileXio_irx, size_fileXio_irx, NULL, 0) ||
        load("poweroff", poweroff_irx, size_poweroff_irx, NULL, 0);
    if (!r) {
        fileXioInit();
        poweroffInit();
        r = load("dev9", ps2dev9_irx, size_ps2dev9_irx, NULL, 0) ||
            load("atad", ps2atad_irx, size_ps2atad_irx, NULL, 0) ||
            load("hdd", ps2hdd_irx, size_ps2hdd_irx, hdd_args, sizeof(hdd_args)) ||
            load("pfs", ps2fs_irx, size_ps2fs_irx, pfs_args, sizeof(pfs_args));
        if (!r) {
            r = fileXioMount("pfs0:", "hdd0:__system", FIO_MT_RDWR);
            if (r < 0)
                snprintf(st_hdd, sizeof(st_hdd), "cannot mount hdd0:__system (%d)", r);
            else {
                strcpy(st_hdd, "OK (hdd0:__system mounted)");
                hdd_ok = 1;
                detect_model();
            }
        }
    }

    SifLoadModule("rom0:SIO2MAN", 0, NULL);
    SifLoadModule("rom0:PADMAN", 0, NULL);
    padInit(0);
    if (padPortOpen(0, 0, padBuf) != 0) {
        for (i = 0; i < 200; i++) {
            int s = padGetState(0, 0);
            if (s == PAD_STATE_STABLE || s == PAD_STATE_FINDCTP1) {
                pad_ok = 1;
                break;
            }
            wait_ms(10);
        }
    }
    read_status();
    build_menu();
    if (!hdd_ok)
        log_msg(C_GRAY, "Only 'Power off PSX' is available.");
    else if (series < 0)
        log_msg(C_RED, "Model not recognised - installing is disabled.");
    else
        log_msg(C_GRAY, "Ready.");
}

int main(int argc, char *argv[])
{
    gfx_init();
    strcpy(prog, "Starting PSX Language Tool ...");
    draw();

    init_all();
    prog[0] = 0;

    for (;;) {
        u32 k;
        int a;
        draw();
        k = wait_key();
        if (!pad_ok)
            pad_ok = 1;
        if (k & PAD_UP)
            sel = (sel + nmenu - 1) % nmenu;
        else if (k & PAD_DOWN)
            sel = (sel + 1) % nmenu;
        else if (k & (PAD_CROSS | PAD_CIRCLE)) {
            a = menu[sel];
            if (a == A_STATUS) {
                read_status();
                log_msg(C_GRAY, "Status refreshed.");
                continue;
            }
            if (!confirm(a)) {
                log_msg(C_GRAY, "Cancelled.");
                continue;
            }
            switch (a) {
            case A_GER:
            case A_ENG:
            case A_POL:
            case A_ESP:     install(a - A_GER); break;
            case A_RESTORE: restore(); break;
            case A_JPN:
                if (ensure_dic_backup() == 0) {
                    if (write_checked(DIC, dic_jpn, size_dic_jpn) < 0)
                        log_msg(C_RED, "Writing jp.dic failed.");
                    else
                        log_msg(C_GREEN, "Japanese button labels restored.");
                }
                break;
            case A_MKBAK:   make_backup(); break;
            case A_OFF:     shutdown_psx(); break;
            }
            prog[0] = 0;
            read_status();
            build_menu();
        }
    }
    return 0;
}
