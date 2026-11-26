#ifndef PS2STUB_H
#define PS2STUB_H
#include <stdint.h>
#include <stdarg.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef uint64_t u64;
/* kernel / sif */
void SleepThread(void); void FlushCache(int);
void SifInitRpc(int); int SifIopReset(const char *, int); int SifIopSync(void);
int SifLoadFileInit(void); int SifLoadModule(const char *, int, const char *);
int SifExecModuleBuffer(void *, unsigned int, unsigned int, const char *, int *);
int sbv_patch_enable_lmb(void); int sbv_patch_disable_prefix_check(void);
/* io */
#define FIO_O_RDONLY 0x0001
#define FIO_O_WRONLY 0x0002
#define FIO_O_RDWR   0x0003
#define FIO_O_CREAT  0x0200
#define FIO_O_TRUNC  0x0400
#define FIO_MT_RDWR  0
#define FIO_S_IFMT  0xF000
#define FIO_S_IFDIR 0x1000
#define FIO_S_IFREG 0x2000
#define FIO_S_ISDIR(m) (((m)&FIO_S_IFMT) == FIO_S_IFDIR)
typedef struct { unsigned int mode, attr, size; unsigned char ctime[8], atime[8], mtime[8]; unsigned int hisize, priv[6]; } iox_stat_t;
int fileXioInit(void);
int fileXioGetStat(const char *, iox_stat_t *);
int fileXioOpen(const char *, int, ...);
int fileXioRead(int, void *, int);
int fileXioWrite(int, const void *, int);
int fileXioClose(int);
int fileXioMkdir(const char *, int);
int fileXioRemove(const char *);
int fileXioUmount(const char *);
int fileXioMount(const char *, const char *, int);
/* pad */
#define PAD_DOWN 0x0040
#define PAD_UP 0x0010
#define PAD_START 0x0008
#define PAD_CROSS 0x4000
#define PAD_CIRCLE 0x2000
#define PAD_STATE_FINDCTP1 0x02
#define PAD_STATE_STABLE 0x06
struct padButtonStatus { u8 ok, mode; u16 btns; };
int padInit(int); int padPortOpen(int, int, void *); int padGetState(int, int);
int padRead(int, int, struct padButtonStatus *);
int poweroffInit(void); void poweroffShutdown(void);
/* debug screen */
void init_scr(void); void scr_printf(const char *, ...); void scr_vprintf(const char *, va_list);
void scr_setXY(int, int); void scr_clear(void); void scr_setbgcolor(u32); void scr_setfontcolor(u32);
void scr_setCursor(int);
#endif
