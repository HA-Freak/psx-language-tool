/* host replacements for the PS2 libraries: pfs0:/ -> $PFSROOT, screen -> line counter */
#include "inc/gsKit.h"
#include "inc/dmaKit.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <io.h>
#include <direct.h>
#include <sys/stat.h>

int fail_write_at = 0;      /* >0: the n-th fileXioWrite from now fails */
int nwrites = 0, nmounts = 0;
int scr_lines = 0, scr_max_lines = 0;

static void map(const char *p, char *out)
{
    if (strncmp(p, "pfs0:/", 6) != 0) { fprintf(stderr, "BAD PATH %s\n", p); exit(9); }
    snprintf(out, 1024, "%s/%s", getenv("PFSROOT"), p + 6);
}
int fileXioGetStat(const char *p, iox_stat_t *st)
{
    char h[1024]; struct _stat s;
    map(p, h);
    { size_t l = strlen(h); if (l && h[l-1] == '/') h[l-1] = 0; }
    if (_stat(h, &s) != 0) return -2;
    memset(st, 0, sizeof(*st));
    st->mode = (s.st_mode & _S_IFDIR) ? FIO_S_IFDIR : FIO_S_IFREG;
    st->size = (unsigned)s.st_size;
    return 0;
}
int fileXioOpen(const char *p, int fl, ...)
{
    char h[1024]; int f = _O_BINARY;
    map(p, h);
    if ((fl & 3) == FIO_O_RDONLY) f |= _O_RDONLY; else if ((fl & 3) == FIO_O_WRONLY) f |= _O_WRONLY; else f |= _O_RDWR;
    if (fl & FIO_O_CREAT) f |= _O_CREAT;
    if (fl & FIO_O_TRUNC) f |= _O_TRUNC;
    { int fd = _open(h, f, _S_IREAD | _S_IWRITE); return fd < 0 ? -2 : fd; }
}
int fileXioRead(int fd, void *b, int n) { return _read(fd, b, n); }
int fileXioWrite(int fd, const void *b, int n)
{
    nwrites++;
    if (fail_write_at > 0 && --fail_write_at == 0) return -5;
    return _write(fd, b, n);
}
int fileXioClose(int fd) { return _close(fd); }
int fileXioMkdir(const char *p, int m) { char h[1024]; map(p, h); return _mkdir(h) ? -17 : 0; }
int fileXioRemove(const char *p) { char h[1024]; map(p, h); return remove(h) ? -2 : 0; }
int fileXioUmount(const char *p) { return 0; }
int fileXioMount(const char *a, const char *b, int f) { nmounts++; return 0; }
int fileXioInit(void) { return 0; }
void SleepThread(void) {}
void SifInitRpc(int a) {} int SifIopReset(const char *a, int b) { return 1; } int SifIopSync(void) { return 1; }
int SifLoadFileInit(void) { return 0; } int SifLoadModule(const char *a, int b, const char *c) { return 0; }
int SifExecModuleBuffer(void *a, unsigned int b, unsigned int c, const char *d, int *e) { return 0; }
int sbv_patch_enable_lmb(void) { return 0; } int sbv_patch_disable_prefix_check(void) { return 0; }
int padInit(int a) { return 1; } int padPortOpen(int a, int b, void *c) { return 1; }
int padGetState(int a, int b) { return PAD_STATE_STABLE; }
u16 next_btn = 0;
static int tog; int padRead(int a, int b, struct padButtonStatus *s) { s->btns = 0xffff ^ ((tog++ & 1) ? PAD_CIRCLE : 0); return 1; }
int poweroffInit(void) { return 0; } void poweroffShutdown(void) {}
static FILE *scr_out;
void init_scr(void) {}
void scr_vprintf(const char *f, va_list ap)
{
    char buf[512]; char *c;
    vsnprintf(buf, sizeof buf, f, ap);
    for (c = buf; *c; c++) if (*c == '\n') { scr_lines++; if (scr_lines > scr_max_lines) scr_max_lines = scr_lines; }
    if (getenv("SCRDUMP")) fputs(buf, stdout);
}
void scr_printf(const char *f, ...) { va_list ap; va_start(ap, f); scr_vprintf(f, ap); va_end(ap); }
void scr_setXY(int x, int y) { scr_lines = y; }
void scr_clear(void) { scr_lines = 0; if (getenv("SCRDUMP")) puts("\n---------- screen ----------"); }
void scr_setbgcolor(u32 c) {} void scr_setfontcolor(u32 c) {} void scr_setCursor(int e) {}

/* gsKit: every uploaded frame can be saved as PPM ($SCRSHOT = file prefix) */
static GSGLOBAL gsg = { 640, 448 };
static int nshot = 0;
int scr_frames = 0;
void FlushCache(int m) {}
GSGLOBAL *gsKit_init_global(void) { if (getenv("SCRPAL")) gsg.Height = 512; return &gsg; }
void gsKit_init_screen(GSGLOBAL *g) {} void gsKit_mode_switch(GSGLOBAL *g, u8 m) {}
u32 gsKit_vram_alloc(GSGLOBAL *g, u32 s, u8 t) { return 0; } u32 gsKit_texture_size(int w, int h, int p) { return w * h * 4; }
void gsKit_texture_upload(GSGLOBAL *g, GSTEXTURE *t)
{
    const char *pre = getenv("SCRSHOT");
    scr_frames++;
    if (pre) {
        char fn[512]; FILE *f; u32 i, *p = t->Mem;
        snprintf(fn, sizeof fn, "%s%02d.ppm", pre, nshot++);
        f = fopen(fn, "wb");
        fprintf(f, "P6 %u %u 255\n", t->Width, t->Height);
        for (i = 0; i < t->Width * t->Height; i++) { fputc(p[i] & 255, f); fputc(p[i] >> 8 & 255, f); fputc(p[i] >> 16 & 255, f); }
        fclose(f);
    }
}
void gsKit_prim_sprite_texture(GSGLOBAL *g, GSTEXTURE *t, float a, float b, float c, float d, float e, float f, float h, float i, int z, u64 col) {}
void gsKit_queue_exec(GSGLOBAL *g) {} void gsKit_sync_flip(GSGLOBAL *g) {}
int dmaKit_init(u32 a, u32 b, u32 c, u32 d, u32 e, u32 f) { return 0; } int dmaKit_chan_init(u32 c) { return 0; }
