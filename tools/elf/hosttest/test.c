/* host test driver: one action per run, like starting the ELF once per action
   usage: test ACTION [failwrite N]   ACTION = status|ger|eng|pol|restore|jpn|mkbak|draw */
#define main gui_main
#include "gui.c"
#undef main
extern int fail_write_at, nwrites, nmounts, scr_max_lines;
extern int scr_frames;
extern u16 next_btn;
int main(int argc, char **argv)
{
    int i;
    const char *a = argv[1];
    if (argc > 3 && !strcmp(argv[2], "failwrite")) fail_write_at = atoi(argv[3]);
    gfx_init();
    pad_ok = 1;
    hdd_ok = 1;
    strcpy(st_hdd, "OK (hdd0:__system mounted)");
    detect_model();
    read_status();
    build_menu();
    printf("before: series=%d fw=%s | model=%s | xmb=%s | dic=%s | bak=%s | menu=%d items\n",
           series, fw, st_model, st_xmb, st_dic, st_bak, nmenu);
    if (!strcmp(a, "ger")) install(0);
    else if (!strcmp(a, "eng")) install(1);
    else if (!strcmp(a, "pol")) install(2);
    else if (!strcmp(a, "restore")) restore();
    else if (!strcmp(a, "mkbak")) make_backup();
    else if (!strcmp(a, "jpn")) {
        if (ensure_dic_backup() == 0) {
            if (write_checked(DIC, dic_jpn, size_dic_jpn) < 0) log_msg(C_RED, "Writing jp.dic failed.");
            else log_msg(C_GREEN, "Japanese button labels restored.");
        }
    } else if (!strcmp(a, "draw")) {
        for (sel = 0; sel < nmenu; sel++) { draw(); confirm(menu[sel]); }
        sel = 0;
    } else if (!strcmp(a, "shots")) {           /* main menu, confirm box, busy, result */
        log_msg(C_GRAY, "Ready.");
        sel = 0; draw();
        asking = A_GER; draw(); asking = -1;
        install(0);
        prog[0] = 0; read_status(); build_menu(); draw();
    }
    read_status();
    printf("after : xmb=%s | dic=%s | bak=%s\n", st_xmb, st_dic, st_bak);
    for (i = 0; i < 4; i++) if (msg[i][0]) printf("  msg: %s\n", msg[i]);
    printf("  writes=%d flushes=%d max_screen_lines=%d\n", nwrites, nmounts, scr_max_lines);
    printf("  frames=%d\n", scr_frames);
    return 0;
}
