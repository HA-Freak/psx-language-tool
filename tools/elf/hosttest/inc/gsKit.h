#include "ps2stub.h"
typedef struct { int Width, Height, PSM, ZBuffering, DoubleBuffering, PrimAlphaEnable; } GSGLOBAL;
typedef struct { u32 Width, Height; u8 PSM; void *Mem; u32 Vram; u8 Filter; } GSTEXTURE;
#define GS_PSM_CT32 0
#define GS_SETTING_OFF 0
#define GS_ONESHOT 1
#define GS_FILTER_NEAREST 0
#define GSKIT_ALLOC_USERBUFFER 1
#define GS_SETREG_RGBAQ(r, g, b, a, q) 0
GSGLOBAL *gsKit_init_global(void);
void gsKit_init_screen(GSGLOBAL *); void gsKit_mode_switch(GSGLOBAL *, u8);
u32 gsKit_vram_alloc(GSGLOBAL *, u32, u8); u32 gsKit_texture_size(int, int, int);
void gsKit_texture_upload(GSGLOBAL *, GSTEXTURE *);
void gsKit_prim_sprite_texture(GSGLOBAL *, GSTEXTURE *, float, float, float, float, float, float, float, float, int, u64);
void gsKit_queue_exec(GSGLOBAL *); void gsKit_sync_flip(GSGLOBAL *);
