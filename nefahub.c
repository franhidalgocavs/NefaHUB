/*
 * NefaHUB  — Hunt & Incense Timer (C / Win32 API)
 * ───────────────────────────────────────────────────────
 * Compile:
 *   gcc -O2 -mwindows -o nefahub_.exe nefahub_.c -lgdi32 -luser32 -lwinmm
 *
 * This is a single-file native Windows application.
 * No external dependencies — only standard Win32 API.
 */

#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <mmsystem.h>

/* ═══════════════════════════════════════════════════════════════
 * CONSTANTS
 * ═══════════════════════════════════════════════════════════════ */

/* ── Colors (COLORREF = 0x00BBGGRR) ───────────────────────── */
#define C_ROOT      RGB(0x0d, 0x0f, 0x1a)
#define C_PANEL     RGB(0x12, 0x14, 0x1f)
#define C_BLOCK     RGB(0x18, 0x1a, 0x28)
#define C_ACCENT    RGB(0x00, 0xff, 0xcc)
#define C_DIM       RGB(0x55, 0x55, 0x77)
#define C_RED       RGB(0xff, 0x33, 0x33)
#define C_ORANGE    RGB(0xff, 0x9f, 0x43)
#define C_GOLD      RGB(0xf4, 0xd0, 0x3f)
#define C_PURPLE    RGB(0xd3, 0x00, 0xff)
#define C_BLUE      RGB(0x00, 0xbc, 0xff)
#define C_GREEN     RGB(0x2e, 0xcc, 0x71)
#define C_CHROMA    RGB(0x01, 0x01, 0x01)
#define C_BAR_IDLE  RGB(0x2a, 0x2a, 0x3a)
#define C_CFG_LINE  RGB(0x22, 0x24, 0x38)
#define C_CFG_DIM   RGB(0x66, 0x66, 0x8a)
#define C_CFG_KEY   RGB(0x44, 0x47, 0x5a)
#define C_HINT_DIM  RGB(0x33, 0x33, 0x55)
#define C_BTN_BG    RGB(0x1a, 0x1c, 0x2e)
#define C_LABEL_FG  RGB(0xaa, 0xaa, 0xcc)

/* ── Titles ───────────────────────────────────────────────── */
#define MAIN_TITLE    L"NefaHUB "
#define OVERLAY_TITLE L"NefaHUBOV"

/* ── Window sizes ─────────────────────────────────────────── */
#define MAIN_W  540
#define MAIN_H  400
#define OV_W    420
#define OV_H    280

/* ── Timer ID ─────────────────────────────────────────────── */
#define TIMER_TICK 1

/* ── Game timing ──────────────────────────────────────────── */
static const char *MAP_KEYS[]   = { "chico", "mediano", "grande" };
static const wchar_t *MAP_LABELS[] = { L"CHICO", L"MEDIANO", L"GRANDE" };
#define MAP_COUNT 3

static const char *HUNT_KEYS[]   = { "baja", "media", "alta" };
static const wchar_t *HUNT_LABELS[] = { L"BAJA", L"MEDIA", L"ALTA" };
#define HUNT_COUNT 3

/* hunt_matrix[difficulty][map_size] in seconds */
static const int HUNT_MATRIX[3][3] = {
    { 15, 30, 40 },  /* baja  */
    { 20, 40, 50 },  /* media */
    { 30, 50, 60 },  /* alta  */
};

#define CURSED_MOD 20

#define IDC_CANCEL    2002
#define IDC_RESET_DEFAULTS 2003
#define IDC_APPLY     2004
#define IDC_MAP_BASE  2100
#define IDC_HUNT_BASE 2200
#define IDC_KEY_BASE  2300
#define IDC_EDIT_BASE 2400
#define IDC_EDIT_CURSED 2500
#define IDC_EDIT_BPM  2501
#define IDC_EDIT_VOLUME 2502

/* ── Default key bindings (virtual key codes) ─────────────── */
/* We store VK codes for simplicity in C */
#define ACT_INCENSE_START    0
#define ACT_INCENSE_PAUSE    1
#define ACT_HUNT             2
#define ACT_CYCLE_MAP        3
#define ACT_TOGGLE_CURSED    4
#define ACT_CYCLE_DIFFICULTY 5
#define ACT_CYCLE_VIEW       6
#define ACT_GHOST_RHYTHM     7
#define ACT_BPM_TAP          8
#define ACT_COUNT            9

static const wchar_t *ACTION_LABELS[ACT_COUNT] = {
    L"Iniciar Incienso",
    L"Pausar Incienso",
    L"Cacer\x00eda / Reset (largo)",
    L"Ciclar Mapa",
    L"Modo Maldita",
    L"Ciclar Dificultad",
    L"Cambiar Vista",
    L"Ritmo Fantasma",
    L"Contador BPM",
};

/* We'll store key names as single scan-code/vk for simplicity.
 * Default: 1, 2, 3, F1, F2, F3, F9, 4, 5 */
static int DEFAULT_KEYS[ACT_COUNT] = {
    '1', '2', '3',
    VK_F1, VK_F2, VK_F3, VK_F9,
    '4', '5'
};

/* ═══════════════════════════════════════════════════════════════
 * APPLICATION STATE
 * ═══════════════════════════════════════════════════════════════ */
typedef struct {
    /* Windows */
    HWND hwnd_main;
    HWND hwnd_overlay;

    /* Game state */
    int    map_idx;
    int    hunt_idx;
    int    is_cursed;
    double hunt_total;
    double hunt_time;
    int    hunt_active;
    double hunt_ref;
    int    has_hunt_ref;
    int    cursed_mod;
    int    hunt_matrix[3][3];

    int    cooldown_active;
    double cooldown_time;

    int    incense_active;
    int    incense_paused;
    int    incense_was_paused;
    double incense_time;

    /* Ghost rhythm */
    int    ghost_active;
    int    global_volume;
    int    ghost_bpm;
    double ghost_interval;
    HANDLE ghost_thread;
    char  *ghost_wav;

    /* BPM tap */
    int    bpm_active;
    double bpm_taps[6];
    int    bpm_tap_count;

    LARGE_INTEGER last_tick;
    double        tick_freq;

    /* View: 0 = normal, 2 = overlay */
    int view_mode;

    /* Key bindings (VK codes) */
    int keys[ACT_COUNT];

    /* Key press tracking for hold detection */
    LARGE_INTEGER key_down_time[256];
    int           key_is_down[256];

    /* Settings dialog */
    HWND hwnd_settings;
    int  capturing_action; /* -1 = not capturing */

    /* Fonts */
    HFONT f_clock_main;
    HFONT f_clock_ov;
    HFONT f_status_main;
    HFONT f_status_ov;
    HFONT f_incense;
    HFONT f_incense_ov;
    HFONT f_incense_ico;
    HFONT f_config_lbl;
    HFONT f_config_val;
    HFONT f_ref_lbl;
    HFONT f_ref_val;
    HFONT f_cfg_hint;
    HFONT f_total;
    HFONT f_settings_title;
    HFONT f_settings_btn;

    /* Window position */
    int win_x, win_y;

    /* Keyboard hook */
    HHOOK kb_hook;

} AppState;

static AppState g_app = {0};

/* ═══════════════════════════════════════════════════════════════
 * FORWARD DECLARATIONS
 * ═══════════════════════════════════════════════════════════════ */
static LRESULT CALLBACK MainWndProc(HWND, UINT, WPARAM, LPARAM);
static LRESULT CALLBACK OverlayWndProc(HWND, UINT, WPARAM, LPARAM);
static LRESULT CALLBACK LowLevelKBProc(int, WPARAM, LPARAM);
static void recalc(void);
static void tick(void);
static void paint_main(HWND hwnd);
static void paint_overlay(HWND hwnd);
static void start_hunt(void);
static void reset_hunt(void);
static void start_incense(void);
static void reset_incense(void);
static void pause_incense(void);
static void cycle_map(void);
static void toggle_cursed(void);
static void cycle_difficulty(void);
static void cycle_view(void);
static void beep_async(int action_id);
static void load_config(void);
static void save_config(void);
static void open_settings(void);
static void invalidate_all(void);

/* ═══════════════════════════════════════════════════════════════
 * UTILITY
 * ═══════════════════════════════════════════════════════════════ */

static double get_time(void) {
    LARGE_INTEGER now;
    QueryPerformanceCounter(&now);
    return (double)now.QuadPart / g_app.tick_freq;
}

static HFONT create_font(const wchar_t *name, int size, int bold) {
    return CreateFontW(
        -size, 0, 0, 0,
        bold ? FW_BOLD : FW_NORMAL,
        FALSE, FALSE, FALSE,
        DEFAULT_CHARSET,
        OUT_TT_PRECIS, CLIP_DEFAULT_PRECIS,
        CLEARTYPE_QUALITY,
        DEFAULT_PITCH | FF_DONTCARE,
        name);
}

static void draw_text_color(HDC hdc, HFONT font, const wchar_t *text,
                            int x, int y, COLORREF color, int align) {
    HFONT old = (HFONT)SelectObject(hdc, font);
    SetTextColor(hdc, color);
    SetBkMode(hdc, TRANSPARENT);
    int ta = SetTextAlign(hdc, align);
    TextOutW(hdc, x, y, text, (int)wcslen(text));
    SelectObject(hdc, old);
    SetTextAlign(hdc, ta);
}

/* Format time as mm:ss.d */
static void format_time(double t, wchar_t *buf, int buflen) {
    const wchar_t *sign = t < 0 ? L"-" : L"";
    double a = fabs(t);
    int m  = (int)(a / 60.0);
    int s  = (int)fmod(a, 60.0);
    int ms = (int)fmod(a * 10.0, 10.0);
    swprintf(buf, buflen, L"%s%02d:%02d.%d", sign, m, s, ms);
}

/* Get key name for display */
static void get_key_name(int vk, wchar_t *buf, int buflen) {
    if (vk >= '0' && vk <= '9') {
        swprintf(buf, buflen, L"%c", (wchar_t)vk);
    } else if (vk >= 'A' && vk <= 'Z') {
        swprintf(buf, buflen, L"%c", (wchar_t)vk);
    } else if (vk >= VK_F1 && vk <= VK_F24) {
        swprintf(buf, buflen, L"F%d", vk - VK_F1 + 1);
    } else if (vk >= VK_NUMPAD0 && vk <= VK_NUMPAD9) {
        swprintf(buf, buflen, L"NUM%d", vk - VK_NUMPAD0);
    } else {
        UINT sc = MapVirtualKeyW(vk, MAPVK_VK_TO_VSC);
        if (sc) {
            GetKeyNameTextW((LONG)(sc << 16), buf, buflen);
        } else {
            swprintf(buf, buflen, L"VK%d", vk);
        }
    }
}

/* ═══════════════════════════════════════════════════════════════
 * SOUND (threaded)
 * ═══════════════════════════════════════════════════════════ */
#define SND_WELCOME       0
#define SND_HUNT_START    1
#define SND_INCENSE_START 2
#define SND_SAFE          3
#define SND_INCENSE_DONE  4
#define SND_CONFIG        5
#define SND_CURSED_ON     6
#define SND_CURSED_OFF    7
#define SND_VIEW          8

static char* create_wav_buffer(int freq, int duration_ms, int volume, double decay);

static void my_beep(int freq, int duration_ms) {
    // Reducimos el volumen de los beeps de interfaz porque
    // las frecuencias altas suenan mucho mas fuerte al oido
    // que el golpe grave de 120Hz del metronomo.
    int beep_vol = g_app.global_volume / 3;
    char *wav = create_wav_buffer(freq, duration_ms, beep_vol, 0.0);
    if (wav) {
        PlaySoundA(wav, NULL, SND_MEMORY | SND_SYNC);
        free(wav);
    }
}

static DWORD WINAPI beep_thread(LPVOID param) {
    int id = (int)(intptr_t)param;
    switch (id) {
        case SND_WELCOME:       my_beep(600,80);  my_beep(900,100); my_beep(1200,130); break;
        case SND_HUNT_START:    my_beep(880,130); my_beep(880,130); break;
        case SND_INCENSE_START: my_beep(523,80);  my_beep(659,80);  my_beep(784,120);  break;
        case SND_SAFE:          my_beep(1047,100);my_beep(1318,100);my_beep(1568,180); break;
        case SND_INCENSE_DONE:  my_beep(784,100); my_beep(659,100); my_beep(523,150);  break;
        case SND_CONFIG:        my_beep(750,80);  break;
        case SND_CURSED_ON:     my_beep(880,80);  my_beep(660,120); break;
        case SND_CURSED_OFF:    my_beep(660,80);  my_beep(880,120); break;
        case SND_VIEW:          my_beep(800,60);  break;
    }
    return 0;
}

static void beep_async(int id) {
    CreateThread(NULL, 0, beep_thread, (LPVOID)(intptr_t)id, 0, NULL);
}

/* ═══════════════════════════════════════════════════════════════
 * CONFIG PERSISTENCE (minimal JSON)
 * ═══════════════════════════════════════════════════════════════ */

static int json_int(const char *json, const char *key, int def) {
    char search[64];
    sprintf(search, "\"%s\"", key);
    const char *p = strstr(json, search);
    if (!p) return def;
    p = strchr(p, ':');
    if (!p) return def;
    return atoi(p + 1);
}

static double json_double(const char *json, const char *key, double def) {
    char search[64];
    sprintf(search, "\"%s\"", key);
    const char *p = strstr(json, search);
    if (!p) return def;
    p = strchr(p, ':');
    if (!p) return def;
    return atof(p + 1);
}

static void get_config_path(wchar_t *path) {
    wchar_t appdata[MAX_PATH];
    GetEnvironmentVariableW(L"APPDATA", appdata, MAX_PATH);
    swprintf(path, MAX_PATH, L"%s\\NefaHUB\\config.json", appdata);
}

static void load_config(void) {
    for (int i = 0; i < ACT_COUNT; i++)
        g_app.keys[i] = DEFAULT_KEYS[i];
    g_app.map_idx  = 1;
    g_app.hunt_idx = 1;
    g_app.win_x = 100;
    g_app.win_y = 100;

    /* Default game times */
    g_app.cursed_mod = 20;
    g_app.hunt_matrix[0][0] = 15; g_app.hunt_matrix[0][1] = 30; g_app.hunt_matrix[0][2] = 40; /* baja */
    g_app.hunt_matrix[1][0] = 20; g_app.hunt_matrix[1][1] = 40; g_app.hunt_matrix[1][2] = 50; /* media */
    g_app.hunt_matrix[2][0] = 30; g_app.hunt_matrix[2][1] = 50; g_app.hunt_matrix[2][2] = 60; /* alta */

    g_app.global_volume = 80;
    g_app.ghost_bpm = 117;
    g_app.ghost_interval = 60.0 / 117.0;

    wchar_t cpath[MAX_PATH];
    get_config_path(cpath);
    FILE *f = _wfopen(cpath, L"rb");
    if (!f) return;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *buf = (char *)malloc(sz + 1);
    if (!buf) { fclose(f); return; }
    fread(buf, 1, sz, f);
    buf[sz] = 0;
    fclose(f);

    g_app.win_x    = json_int(buf, "window_x",        g_app.win_x);
    g_app.win_y    = json_int(buf, "window_y",        g_app.win_y);
    g_app.map_idx  = json_int(buf, "default_map_idx",  g_app.map_idx);
    g_app.hunt_idx = json_int(buf, "default_hunt_idx", g_app.hunt_idx);
    g_app.cursed_mod = json_int(buf, "cursed_mod", g_app.cursed_mod);
    g_app.global_volume = json_int(buf, "global_volume", 80);
    if (g_app.global_volume < 0 || g_app.global_volume > 100) g_app.global_volume = 80;
    
    g_app.ghost_bpm = json_int(buf, "ghost_bpm", 117);
    g_app.ghost_interval = 60.0 / g_app.ghost_bpm;

    g_app.hunt_matrix[0][0] = json_int(buf, "time_baja_chico",   g_app.hunt_matrix[0][0]);
    g_app.hunt_matrix[0][1] = json_int(buf, "time_baja_mediano", g_app.hunt_matrix[0][1]);
    g_app.hunt_matrix[0][2] = json_int(buf, "time_baja_grande",  g_app.hunt_matrix[0][2]);
    g_app.hunt_matrix[1][0] = json_int(buf, "time_media_chico",  g_app.hunt_matrix[1][0]);
    g_app.hunt_matrix[1][1] = json_int(buf, "time_media_mediano", g_app.hunt_matrix[1][1]);
    g_app.hunt_matrix[1][2] = json_int(buf, "time_media_grande",  g_app.hunt_matrix[1][2]);
    g_app.hunt_matrix[2][0] = json_int(buf, "time_alta_chico",   g_app.hunt_matrix[2][0]);
    g_app.hunt_matrix[2][1] = json_int(buf, "time_alta_mediano", g_app.hunt_matrix[2][1]);
    g_app.hunt_matrix[2][2] = json_int(buf, "time_alta_grande",  g_app.hunt_matrix[2][2]);

    /* Load key bindings */
    for (int i = 0; i < ACT_COUNT; i++) {
        char kname[32];
        sprintf(kname, "key_%d", i);
        int v = json_int(buf, kname, -1);
        if (v > 0) g_app.keys[i] = v;
    }

    free(buf);
}

static void save_config(void) {
    RECT r;
    HWND w = (g_app.view_mode == 2) ? g_app.hwnd_overlay : g_app.hwnd_main;
    GetWindowRect(w, &r);

    wchar_t appdata[MAX_PATH];
    GetEnvironmentVariableW(L"APPDATA", appdata, MAX_PATH);

    wchar_t dir[MAX_PATH];
    swprintf(dir, MAX_PATH, L"%s\\NefaHUB", appdata);
    CreateDirectoryW(dir, NULL);

    wchar_t cpath[MAX_PATH];
    swprintf(cpath, MAX_PATH, L"%s\\config.json", dir);

    FILE *f = _wfopen(cpath, L"w");
    if (!f) return;
    fprintf(f, "{\n");
    fprintf(f, "  \"window_x\": %ld,\n", r.left);
    fprintf(f, "  \"window_y\": %ld,\n", r.top);
    fprintf(f, "  \"default_map_idx\": %d,\n", g_app.map_idx);
    fprintf(f, "  \"default_hunt_idx\": %d,\n", g_app.hunt_idx);
    fprintf(f, "  \"cursed_mod\": %d,\n", g_app.cursed_mod);
    fprintf(f, "  \"time_baja_chico\": %d,\n", g_app.hunt_matrix[0][0]);
    fprintf(f, "  \"time_baja_mediano\": %d,\n", g_app.hunt_matrix[0][1]);
    fprintf(f, "  \"time_baja_grande\": %d,\n", g_app.hunt_matrix[0][2]);
    fprintf(f, "  \"time_media_chico\": %d,\n", g_app.hunt_matrix[1][0]);
    fprintf(f, "  \"time_media_mediano\": %d,\n", g_app.hunt_matrix[1][1]);
    fprintf(f, "  \"time_media_grande\": %d,\n", g_app.hunt_matrix[1][2]);
    fprintf(f, "  \"time_alta_chico\": %d,\n", g_app.hunt_matrix[2][0]);
    fprintf(f, "  \"time_alta_mediano\": %d,\n", g_app.hunt_matrix[2][1]);
    fprintf(f, "  \"time_alta_grande\": %d,\n", g_app.hunt_matrix[2][2]);
    fprintf(f, "  \"global_volume\": %d,\n", g_app.global_volume);
    fprintf(f, "  \"ghost_bpm\": %d,\n", g_app.ghost_bpm);
    for (int i = 0; i < ACT_COUNT; i++) {
        fprintf(f, "  \"key_%d\": %d%s\n", i, g_app.keys[i],
                (i < ACT_COUNT - 1) ? "," : "");
    }
    fprintf(f, "}\n");
    fclose(f);
}

/* ═══════════════════════════════════════════════════════════════
 * GAME LOGIC
 * ═══════════════════════════════════════════════════════════════ */

static char* create_wav_buffer(int freq, int duration_ms, int volume, double decay) {
    int sample_rate = 44100;
    int num_samples = sample_rate * duration_ms / 1000;
    if (volume < 0) volume = 0;
    if (volume > 100) volume = 100;
    int amplitude = (int)(32767.0 * volume / 100.0);
    
    int data_size = num_samples * sizeof(short);
    int total_size = 44 + data_size;
    char *wav = (char *)malloc(total_size);
    if (!wav) return NULL;
    
    char *p = wav;
    memcpy(p, "RIFF", 4); p += 4;
    int chunk_size = 36 + data_size;
    memcpy(p, &chunk_size, 4); p += 4;
    memcpy(p, "WAVE", 4); p += 4;
    
    memcpy(p, "fmt ", 4); p += 4;
    int fmt_size = 16;
    memcpy(p, &fmt_size, 4); p += 4;
    short audio_format = 1;
    memcpy(p, &audio_format, 2); p += 2;
    short num_channels = 1;
    memcpy(p, &num_channels, 2); p += 2;
    memcpy(p, &sample_rate, 4); p += 4;
    int byte_rate = sample_rate * 2;
    memcpy(p, &byte_rate, 4); p += 4;
    short block_align = 2;
    memcpy(p, &block_align, 2); p += 2;
    short bits_per_sample = 16;
    memcpy(p, &bits_per_sample, 2); p += 2;
    
    memcpy(p, "data", 4); p += 4;
    memcpy(p, &data_size, 4); p += 4;
    
    short *samples = (short *)p;
    for (int i = 0; i < num_samples; i++) {
        double t = (double)i / sample_rate;
        double env = (decay > 0) ? exp(-decay * t) : 1.0;
        samples[i] = (short)(amplitude * env * sin(2 * 3.14159265358979323846 * freq * t));
    }
    return wav;
}

static void generate_beep_wav(int freq, int duration_ms, int volume, double decay) {
    if (g_app.ghost_wav) {
        free(g_app.ghost_wav);
        g_app.ghost_wav = NULL;
    }
    g_app.ghost_wav = create_wav_buffer(freq, duration_ms, volume, decay);
}

static DWORD WINAPI ghost_rhythm_loop(LPVOID param) {
    (void)param;
    double next_beat = get_time();
    while (g_app.ghost_active) {
        if (g_app.ghost_wav) {
            PlaySoundA(g_app.ghost_wav, NULL, SND_MEMORY | SND_ASYNC);
        }
        next_beat += g_app.ghost_interval;
        
        while (g_app.ghost_active) {
            double now = get_time();
            if (now >= next_beat) break;
            double diff = next_beat - now;
            if (diff > 0.01) Sleep(1);
            else Sleep(0);
        }
    }
    return 0;
}

static void toggle_ghost_rhythm(void) {
    g_app.ghost_active = !g_app.ghost_active;
    if (g_app.ghost_active) {
        // beep_async(SND_CONFIG);
        generate_beep_wav(120, 30, g_app.global_volume, 45.0);
        g_app.ghost_thread = CreateThread(NULL, 0, ghost_rhythm_loop, NULL, 0, NULL);
    } else {
        PlaySoundA(NULL, NULL, 0);
    }
    invalidate_all();
}

static void reset_bpm(void) {
    g_app.bpm_tap_count = 0;
    g_app.bpm_active = 0;
    invalidate_all();
}

static void on_bpm_tap(void) {
    double now = get_time();
    if (g_app.bpm_tap_count > 0 && now - g_app.bpm_taps[g_app.bpm_tap_count - 1] > 10.0) {
        g_app.bpm_tap_count = 0;
    }
    
    if (g_app.bpm_tap_count < 6) {
        g_app.bpm_taps[g_app.bpm_tap_count++] = now;
    } else {
        for (int i = 0; i < 5; i++) g_app.bpm_taps[i] = g_app.bpm_taps[i+1];
        g_app.bpm_taps[5] = now;
    }
    
    g_app.bpm_active = 1;
    invalidate_all();
}

static void recalc(void) {
    int base = g_app.hunt_matrix[g_app.hunt_idx][g_app.map_idx];
    g_app.hunt_total = (double)(base + (g_app.is_cursed ? g_app.cursed_mod : 0));

    if (!g_app.hunt_active && !g_app.cooldown_active) {
        g_app.hunt_time = g_app.hunt_total;
    }
    invalidate_all();
}

static COLORREF incense_color(void) {
    double t = g_app.incense_time;
    if (t < 5.0 || (t >= 20.0 && t < 25.0) || (t >= 60.0 && t < 90.0))
        return C_RED;
    return C_ACCENT;
}

static void start_hunt(void) {
    if (g_app.hunt_active) {
        /* Already hunting — skip to cooldown */
        g_app.hunt_time = 0.0;
        g_app.hunt_active = 0;
        g_app.cooldown_active = 1;
        g_app.cooldown_time = 0.0;
        g_app.hunt_ref = g_app.hunt_total;
        g_app.has_hunt_ref = 1;
        // beep_async(SND_SAFE);
        invalidate_all();
        return;
    }
    g_app.hunt_active = 1;
    g_app.hunt_time   = g_app.hunt_total;
    g_app.cooldown_active = 0;
    // beep_async(SND_HUNT_START);
    invalidate_all();
}

static void reset_hunt(void) {
    g_app.hunt_active = 0;
    g_app.cooldown_active = 0;
    g_app.hunt_time = g_app.hunt_total;
    // beep_async(SND_SAFE);
    invalidate_all();
}

static void start_incense(void) {
    if (g_app.incense_active) {
        if (g_app.incense_paused || g_app.incense_was_paused) {
            /* Paused or was paused: always restart */
            g_app.incense_time   = 0.0;
            g_app.incense_paused = 0;
            g_app.incense_was_paused = 0;
            // beep_async(SND_INCENSE_START);
            invalidate_all();
            return;
        }
        if (g_app.incense_time < 60.0)
            return;  /* blocked during first minute */
        /* After 1 min: restart */
        g_app.incense_time   = 0.0;
        g_app.incense_paused = 0;
        g_app.incense_was_paused = 0;
        // beep_async(SND_INCENSE_START);
        invalidate_all();
        return;
    }
    g_app.incense_active = 1;
    g_app.incense_paused = 0;
    g_app.incense_was_paused = 0;
    g_app.incense_time   = 0.0;
    // beep_async(SND_INCENSE_START);
    invalidate_all();
}

static void reset_incense(void) {
    g_app.incense_active = 0;
    g_app.incense_paused = 0;
    g_app.incense_was_paused = 0;
    g_app.incense_time = 0.0;
    // beep_async(SND_INCENSE_DONE);
    invalidate_all();
}

static void pause_incense(void) {
    if (!g_app.incense_active) return;
    g_app.incense_paused = !g_app.incense_paused;
    if (g_app.incense_paused) {
        g_app.incense_was_paused = 1;
    }
    beep_async(SND_CONFIG);
    invalidate_all();
}

static void cycle_map(void) {
    double old = g_app.hunt_total;
    g_app.map_idx = (g_app.map_idx + 1) % MAP_COUNT;
    beep_async(SND_CONFIG);
    recalc();
    if (g_app.hunt_active) {
        g_app.hunt_time += (g_app.hunt_total - old);
    } else if (g_app.cooldown_active) {
        g_app.cooldown_time -= (g_app.hunt_total - old);
    }
}

static void toggle_cursed(void) {
    g_app.is_cursed = !g_app.is_cursed;
    beep_async(g_app.is_cursed ? SND_CURSED_ON : SND_CURSED_OFF);

    if (g_app.hunt_active) {
        g_app.hunt_time += g_app.is_cursed ? g_app.cursed_mod : -g_app.cursed_mod;
        recalc();
    } else if (g_app.cooldown_active) {
        g_app.cooldown_time += g_app.is_cursed ? -g_app.cursed_mod : g_app.cursed_mod;
        recalc();
    } else {
        recalc();
    }
}

static void cycle_difficulty(void) {
    double old = g_app.hunt_total;
    g_app.hunt_idx = (g_app.hunt_idx + 1) % HUNT_COUNT;
    beep_async(SND_CONFIG);
    recalc();
    if (g_app.hunt_active) {
        g_app.hunt_time += (g_app.hunt_total - old);
    } else if (g_app.cooldown_active) {
        g_app.cooldown_time -= (g_app.hunt_total - old);
    }
}

static void cycle_view(void) {
    beep_async(SND_VIEW);
    RECT r;
    HWND src = (g_app.view_mode == 2) ? g_app.hwnd_overlay : g_app.hwnd_main;
    GetWindowRect(src, &r);

    if (g_app.view_mode == 0) {
        g_app.view_mode = 2;
        ShowWindow(g_app.hwnd_main, SW_HIDE);
        SetWindowPos(g_app.hwnd_overlay, HWND_TOPMOST,
                     r.left, r.top, OV_W, OV_H, SWP_SHOWWINDOW);
        /* Re-apply click-through */
        LONG ex = GetWindowLongW(g_app.hwnd_overlay, GWL_EXSTYLE);
        SetWindowLongW(g_app.hwnd_overlay, GWL_EXSTYLE,
                       ex | WS_EX_LAYERED | WS_EX_TRANSPARENT);
    } else {
        g_app.view_mode = 0;
        ShowWindow(g_app.hwnd_overlay, SW_HIDE);
        SetWindowPos(g_app.hwnd_main, HWND_TOPMOST,
                     r.left, r.top, MAIN_W, MAIN_H, SWP_SHOWWINDOW);
    }
    invalidate_all();
}

/* ── Tick (called every 50ms via WM_TIMER) ──────────────── */
static void tick(void) {
    LARGE_INTEGER now;
    QueryPerformanceCounter(&now);
    double dt = (double)(now.QuadPart - g_app.last_tick.QuadPart) / g_app.tick_freq;
    g_app.last_tick = now;

    int need_repaint = 0;

    if (g_app.bpm_active && g_app.bpm_tap_count > 0 && (get_time() - g_app.bpm_taps[g_app.bpm_tap_count - 1] > 10.0)) {
        reset_bpm();
    }

    if (g_app.hunt_active) {
        g_app.hunt_time -= dt;
        if (g_app.hunt_time <= 0) {
            double excess = fabs(g_app.hunt_time);
            g_app.hunt_time = 0.0;
            g_app.hunt_active = 0;

            if (excess >= 25.0) {
                g_app.cooldown_active = 0;
                g_app.hunt_time = g_app.hunt_total;
                // beep_async(SND_SAFE);
            } else {
                g_app.cooldown_active = 1;
                g_app.cooldown_time = excess;
                g_app.hunt_ref = g_app.hunt_total;
                g_app.has_hunt_ref = 1;
                // beep_async(SND_SAFE);
            }
        }
        need_repaint = 1;
    } else if (g_app.cooldown_active) {
        g_app.cooldown_time += dt;
        if (g_app.cooldown_time >= 25.0) {
            g_app.cooldown_active = 0;
            g_app.cooldown_time = 25.0;
            g_app.hunt_time = g_app.hunt_total;
        }
        need_repaint = 1;
    }

    if (g_app.incense_active && !g_app.incense_paused) {
        g_app.incense_time += dt;
        need_repaint = 1;
    }

    if (need_repaint) invalidate_all();
}

static void invalidate_all(void) {
    if (g_app.hwnd_main && IsWindowVisible(g_app.hwnd_main))
        InvalidateRect(g_app.hwnd_main, NULL, FALSE);
    if (g_app.hwnd_overlay && IsWindowVisible(g_app.hwnd_overlay))
        InvalidateRect(g_app.hwnd_overlay, NULL, FALSE);
}

/* ═══════════════════════════════════════════════════════════════
 * PAINTING — MAIN WINDOW
 * ═══════════════════════════════════════════════════════════════ */

static void fill_rect_color(HDC hdc, int x, int y, int w, int h, COLORREF c) {
    HBRUSH br = CreateSolidBrush(c);
    RECT r = { x, y, x + w, y + h };
    FillRect(hdc, &r, br);
    DeleteObject(br);
}

static void paint_main(HWND hwnd) {
    PAINTSTRUCT ps;
    HDC hdc_screen = BeginPaint(hwnd, &ps);

    RECT cr;
    GetClientRect(hwnd, &cr);
    int cw = cr.right, ch = cr.bottom;

    /* Double buffer */
    HDC hdc = CreateCompatibleDC(hdc_screen);
    HBITMAP bmp = CreateCompatibleBitmap(hdc_screen, cw, ch);
    HBITMAP old_bmp = (HBITMAP)SelectObject(hdc, bmp);

    /* Background */
    fill_rect_color(hdc, 0, 0, cw, ch, C_ROOT);

    /* ── LEFT: Config Panel ─────────────────────────────── */
    int panel_w = 180;
    int px = 10, py = 10;
    fill_rect_color(hdc, px, py, panel_w, ch - 20, C_PANEL);

    /* Title */
    draw_text_color(hdc, g_app.f_config_val, L"CONFIGURACIÓN",
                    px + panel_w/2, py + 8, C_ACCENT, TA_CENTER | TA_TOP);

    /* Map */
    int row_y = py + 35;
    draw_text_color(hdc, g_app.f_config_lbl, L"F1  MAPA:",
                    px + 8, row_y, C_CFG_DIM, TA_LEFT | TA_TOP);
    draw_text_color(hdc, g_app.f_config_val, MAP_LABELS[g_app.map_idx],
                    px + 90, row_y, RGB(0xff,0xff,0xff), TA_LEFT | TA_TOP);

    /* Cursed */
    row_y += 20;
    draw_text_color(hdc, g_app.f_config_lbl, L"F2  MODO:",
                    px + 8, row_y, C_CFG_DIM, TA_LEFT | TA_TOP);
    if (g_app.is_cursed) {
        wchar_t cursed_txt[32];
        swprintf(cursed_txt, 32, L"MALDITA \xD83D\xDC80 +%ds", g_app.cursed_mod);
        draw_text_color(hdc, g_app.f_config_val, cursed_txt,
                        px + 90, row_y, C_PURPLE, TA_LEFT | TA_TOP);
    } else {
        draw_text_color(hdc, g_app.f_config_val, L"NORMAL     +0s",
                        px + 90, row_y, C_BLUE, TA_LEFT | TA_TOP);
    }

    /* Difficulty */
    row_y += 20;
    draw_text_color(hdc, g_app.f_config_lbl, L"F3  DIF:",
                    px + 8, row_y, C_CFG_DIM, TA_LEFT | TA_TOP);
    draw_text_color(hdc, g_app.f_config_val, HUNT_LABELS[g_app.hunt_idx],
                    px + 90, row_y, RGB(0xff,0xff,0xff), TA_LEFT | TA_TOP);

    /* Separator */
    row_y += 25;
    fill_rect_color(hdc, px + 8, row_y, panel_w - 16, 1, C_CFG_LINE);

    /* Total */
    row_y += 8;
    wchar_t total_buf[32];
    swprintf(total_buf, 32, L"TOTAL: %ds", (int)g_app.hunt_total);
    draw_text_color(hdc, g_app.f_total, total_buf,
                    px + panel_w/2, row_y, C_ACCENT, TA_CENTER | TA_TOP);

    /* Separator */
    row_y += 22;
    fill_rect_color(hdc, px + 8, row_y, panel_w - 16, 1, C_CFG_LINE);

    /* Hotkey hints */
    row_y += 8;
    wchar_t hint[64];
    wchar_t kn[16];

    get_key_name(g_app.keys[ACT_INCENSE_START], kn, 16);
    swprintf(hint, 64, L"[%s]  Incienso", kn);
    draw_text_color(hdc, g_app.f_config_lbl, hint,
                    px + 8, row_y, C_CFG_KEY, TA_LEFT | TA_TOP);

    row_y += 14;
    get_key_name(g_app.keys[ACT_INCENSE_PAUSE], kn, 16);
    swprintf(hint, 64, L"[%s]  Pausa", kn);
    draw_text_color(hdc, g_app.f_config_lbl, hint,
                    px + 8, row_y, C_CFG_KEY, TA_LEFT | TA_TOP);

    row_y += 14;
    get_key_name(g_app.keys[ACT_HUNT], kn, 16);
    swprintf(hint, 64, L"[%s]  Cacer\x00eda", kn);
    draw_text_color(hdc, g_app.f_config_lbl, hint,
                    px + 8, row_y, C_CFG_KEY, TA_LEFT | TA_TOP);

    row_y += 14;
    get_key_name(g_app.keys[ACT_CYCLE_VIEW], kn, 16);
    swprintf(hint, 64, L"[%s]  Vista", kn);
    draw_text_color(hdc, g_app.f_config_lbl, hint,
                    px + 8, row_y, C_CFG_KEY, TA_LEFT | TA_TOP);

    row_y += 24;
    get_key_name(g_app.keys[ACT_GHOST_RHYTHM], kn, 16);
    swprintf(hint, 64, L"\xD83D\xDC7B [%s] RITMO %s", kn, g_app.ghost_active ? L"\x25CF" : L"\x25CB");
    draw_text_color(hdc, g_app.f_config_lbl, hint,
                    px + 8, row_y, g_app.ghost_active ? C_ACCENT : C_DIM, TA_LEFT | TA_TOP);

    row_y += 18;
    if (g_app.bpm_tap_count >= 2) {
        double total_dur = g_app.bpm_taps[g_app.bpm_tap_count - 1] - g_app.bpm_taps[0];
        double avg_dur = total_dur / (g_app.bpm_tap_count - 1);
        double bpm = (avg_dur > 0) ? (60.0 / avg_dur) : 0;
        double speed = bpm / (60.0 + bpm * 0.075);
        swprintf(hint, 64, L"BPM: %.0f (%.2f m/s)", bpm, speed);
        draw_text_color(hdc, g_app.f_status_main, hint,
                        px + 8, row_y, C_ACCENT, TA_LEFT | TA_TOP);
    } else {
        draw_text_color(hdc, g_app.f_status_main, L"BPM: ---",
                        px + 8, row_y, C_ACCENT, TA_LEFT | TA_TOP);
    }

    /* ── RIGHT: HUD Panel ───────────────────────────────── */
    int hud_x = px + panel_w + 8;
    int hud_w = cw - hud_x - 10;

    /* ── Incense block (top) ─────────────────────────── */
    int ib_y = py;
    int ib_h = 45;
    fill_rect_color(hdc, hud_x, ib_y, hud_w, ib_h, C_BLOCK);

    /* Incense status text */
    COLORREF inc_col;
    const wchar_t *inc_status;
    if (!g_app.incense_active) {
        inc_col = C_DIM;
        inc_status = L"INCIENSO";
    } else if (g_app.incense_paused) {
        inc_col = C_ORANGE;
        inc_status = L"\x23F8 PAUSADO";
    } else {
        inc_col = incense_color();
        inc_status = L"\xD83D\xDD25 INCIENSO";
    }

    draw_text_color(hdc, g_app.f_config_val, inc_status,
                    hud_x + 10, ib_y + 14, inc_col, TA_LEFT | TA_TOP);

    /* Incense clock */
    wchar_t inc_buf[16];
    format_time(g_app.incense_time, inc_buf, 16);
    draw_text_color(hdc, g_app.f_incense, inc_buf,
                    hud_x + hud_w - 10, ib_y + 10, inc_col, TA_RIGHT | TA_TOP);

    /* ── Hunt block (bottom) ──────────────────────────── */
    int hb_y = ib_y + ib_h + 6;
    int hb_h = ch - hb_y - 10;
    fill_rect_color(hdc, hud_x, hb_y, hud_w, hb_h, C_BLOCK);

    /* Status */
    COLORREF status_col;
    const wchar_t *status_txt;
    if (g_app.hunt_active) {
        status_col = g_app.is_cursed ? C_PURPLE : C_RED;
        status_txt = L"\x26A0 CACER\x00cdA \x26A0";
    } else if (g_app.cooldown_active) {
        status_col = C_BLUE;
        status_txt = L"ENFRIAMIENTO";
    } else {
        status_col = C_ACCENT;
        status_txt = L"";
    }
    draw_text_color(hdc, g_app.f_status_main, status_txt,
                    hud_x + 10, hb_y + 8, status_col, TA_LEFT | TA_TOP);

    /* Reference (ÚLTIMO) */
    draw_text_color(hdc, g_app.f_ref_lbl, L"\x00daLTIMO",
                    hud_x + hud_w - 10, hb_y + 6, C_HINT_DIM, TA_RIGHT | TA_TOP);
    wchar_t ref_buf[16];
    if (g_app.has_hunt_ref) {
        format_time(g_app.hunt_ref, ref_buf, 16);
        draw_text_color(hdc, g_app.f_ref_val, ref_buf,
                        hud_x + hud_w - 10, hb_y + 18, C_GOLD, TA_RIGHT | TA_TOP);
    } else {
        draw_text_color(hdc, g_app.f_ref_val, L"--:--.-",
                        hud_x + hud_w - 10, hb_y + 18, C_DIM, TA_RIGHT | TA_TOP);
    }

    /* Config hint [CB] */
    wchar_t cfg_hint[8];
    swprintf(cfg_hint, 8, L"[%c%c]",
             MAP_KEYS[g_app.map_idx][0] - 32,    /* uppercase */
             HUNT_KEYS[g_app.hunt_idx][0] - 32);
    draw_text_color(hdc, g_app.f_cfg_hint, cfg_hint,
                    hud_x + 10, hb_y + 50, C_CFG_KEY, TA_LEFT | TA_TOP);

    /* Hunt clock */
    double clock_val;
    const wchar_t *state;
    if (g_app.hunt_active) {
        clock_val = g_app.hunt_time;
        state = L"hunt";
    } else if (g_app.cooldown_active) {
        clock_val = g_app.cooldown_time;
        state = L"cooldown";
    } else {
        clock_val = g_app.hunt_time;
        state = L"idle";
    }

    wchar_t clock_buf[16];
    format_time(clock_val, clock_buf, 16);

    COLORREF clock_fg;
    if (wcscmp(state, L"idle") == 0) {
        clock_fg = g_app.is_cursed ? C_PURPLE : C_DIM;
    } else if (wcscmp(state, L"hunt") == 0) {
        if (g_app.is_cursed)
            clock_fg = C_PURPLE;
        else {
            DWORD t = GetTickCount();
            clock_fg = ((t / 333) % 2 == 0) ? C_RED : C_ORANGE;
        }
    } else { /* cooldown */
        if (clock_val < 0 && g_app.is_cursed)
            clock_fg = C_PURPLE;
        else if (clock_val >= 20.0)
            clock_fg = C_RED;
        else
            clock_fg = C_BLUE;
    }

    draw_text_color(hdc, g_app.f_clock_main, clock_buf,
                    hud_x + 70, hb_y + 42, clock_fg, TA_LEFT | TA_TOP);

    /* Progress bar */
    int bar_x = hud_x + 10;
    int bar_y = hb_y + hb_h - 20;
    int bar_w = hud_w - 20;
    int bar_h = 8;
    fill_rect_color(hdc, bar_x, bar_y, bar_w, bar_h, C_ROOT);

    double pct = 0;
    COLORREF bar_col = C_BAR_IDLE;
    if (wcscmp(state, L"hunt") == 0) {
        pct = (g_app.hunt_total > 0) ? fmax(0, clock_val / g_app.hunt_total) : 0;
        if (g_app.is_cursed) bar_col = C_PURPLE;
        else if (pct > 0.6) bar_col = C_RED;
        else if (pct > 0.3) bar_col = C_ORANGE;
        else bar_col = C_ACCENT;
    } else if (wcscmp(state, L"cooldown") == 0) {
        pct = fmin(1.0, fmax(0, clock_val / 25.0));
        bar_col = (clock_val >= 20.0) ? C_RED : C_BLUE;
    } else {
        pct = (g_app.hunt_total > 0) ? fmin(1.0, fmax(0, clock_val / g_app.hunt_total)) : 0;
        bar_col = C_BAR_IDLE;
    }
    int fill_w = (int)(bar_w * pct);
    if (fill_w > 0)
        fill_rect_color(hdc, bar_x, bar_y, fill_w, bar_h, bar_col);

    /* Blit */
    BitBlt(hdc_screen, 0, 0, cw, ch, hdc, 0, 0, SRCCOPY);
    SelectObject(hdc, old_bmp);
    DeleteObject(bmp);
    DeleteDC(hdc);

    EndPaint(hwnd, &ps);
}

/* ═══════════════════════════════════════════════════════════════
 * PAINTING — OVERLAY
 * ═══════════════════════════════════════════════════════════════ */

static void paint_overlay(HWND hwnd) {
    PAINTSTRUCT ps;
    HDC hdc_screen = BeginPaint(hwnd, &ps);

    RECT cr;
    GetClientRect(hwnd, &cr);
    int cw = cr.right, ch = cr.bottom;

    HDC hdc = CreateCompatibleDC(hdc_screen);
    HBITMAP bmp = CreateCompatibleBitmap(hdc_screen, cw, ch);
    HBITMAP old_bmp = (HBITMAP)SelectObject(hdc, bmp);

    /* Chroma background */
    fill_rect_color(hdc, 0, 0, cw, ch, C_CHROMA);

    int y = 10;

    /* ── Incense row (top) ─────────────────────────────── */
    COLORREF inc_col;
    const wchar_t *inc_lbl;
    if (!g_app.incense_active) {
        inc_col = C_DIM;
        inc_lbl = L"\xD83D\xDCA8";
    } else if (g_app.incense_paused) {
        inc_col = C_ORANGE;
        inc_lbl = L"\xD83D\xDCA8";
    } else {
        inc_col = incense_color();
        inc_lbl = L"\xD83D\xDCA8";
    }

    draw_text_color(hdc, g_app.f_incense_ico, inc_lbl,
                    10, y, inc_col, TA_LEFT | TA_TOP);

    wchar_t inc_buf[16];
    if (!g_app.incense_active && g_app.incense_time == 0.0) {
        wcscpy(inc_buf, L"00:00.0");
    } else {
        format_time(g_app.incense_time, inc_buf, 16);
    }
    draw_text_color(hdc, g_app.f_incense_ov, inc_buf,
                    70, y, inc_col, TA_LEFT | TA_TOP);

    /* ── Hunt status (middle) ──────────────────────────── */
    y += 60;
    COLORREF status_col;
    const wchar_t *status_txt;
    if (g_app.hunt_active) {
        status_col = g_app.is_cursed ? C_PURPLE : C_RED;
        status_txt = L"\x26A0 CACER\x00cdA \x26A0";
    } else if (g_app.cooldown_active) {
        status_col = C_BLUE;
        status_txt = L"ENFRIAMIENTO";
    } else {
        status_col = C_ACCENT;
        status_txt = L"";
    }
    draw_text_color(hdc, g_app.f_status_ov, status_txt,
                    10, y, status_col, TA_LEFT | TA_TOP);

    /* ── Config hint + Hunt clock ──────────────────────── */
    y += 18;
    wchar_t cfg_hint[8];
    swprintf(cfg_hint, 8, L"[%c%c]",
             MAP_KEYS[g_app.map_idx][0] - 32,
             HUNT_KEYS[g_app.hunt_idx][0] - 32);
    draw_text_color(hdc, g_app.f_cfg_hint, cfg_hint,
                    10, y + 15, C_CFG_KEY, TA_LEFT | TA_TOP);

    double clock_val;
    COLORREF clock_fg;
    if (g_app.hunt_active) {
        clock_val = g_app.hunt_time;
        if (g_app.is_cursed)
            clock_fg = C_PURPLE;
        else {
            DWORD t = GetTickCount();
            clock_fg = ((t / 333) % 2 == 0) ? C_RED : C_ORANGE;
        }
    } else if (g_app.cooldown_active) {
        clock_val = g_app.cooldown_time;
        if (clock_val < 0 && g_app.is_cursed)
            clock_fg = C_PURPLE;
        else if (clock_val >= 20.0)
            clock_fg = C_RED;
        else
            clock_fg = C_BLUE;
    } else {
        clock_val = g_app.hunt_time;
        clock_fg = g_app.is_cursed ? C_PURPLE : C_DIM;
    }

    wchar_t clock_buf[16];
    format_time(clock_val, clock_buf, 16);
    draw_text_color(hdc, g_app.f_clock_ov, clock_buf,
                    55, y, clock_fg, TA_LEFT | TA_TOP);

    /* ── BPM Counter ────────────────────────────────────── */
    y += 50;
    wchar_t bpm_hint[64];
    if (g_app.bpm_tap_count >= 2) {
        double total_dur = g_app.bpm_taps[g_app.bpm_tap_count - 1] - g_app.bpm_taps[0];
        double avg_dur = total_dur / (g_app.bpm_tap_count - 1);
        double bpm = (avg_dur > 0) ? (60.0 / avg_dur) : 0;
        double speed = bpm / (60.0 + bpm * 0.075);
        swprintf(bpm_hint, 64, L"BPM: %.0f (%.2f m/s)", bpm, speed);
        draw_text_color(hdc, g_app.f_cfg_hint, bpm_hint,
                        10, y, C_ACCENT, TA_LEFT | TA_TOP);
    } else {
        draw_text_color(hdc, g_app.f_cfg_hint, L"BPM: ---",
                        10, y, C_DIM, TA_LEFT | TA_TOP);
    }

    /* Blit */
    BitBlt(hdc_screen, 0, 0, cw, ch, hdc, 0, 0, SRCCOPY);
    SelectObject(hdc, old_bmp);
    DeleteObject(bmp);
    DeleteDC(hdc);

    EndPaint(hwnd, &ps);
}

/* ═══════════════════════════════════════════════════════════════
 * LOW-LEVEL KEYBOARD HOOK
 * ═══════════════════════════════════════════════════════════════ */

static LRESULT CALLBACK LowLevelKBProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode != HC_ACTION)
        return CallNextHookEx(g_app.kb_hook, nCode, wParam, lParam);

    KBDLLHOOKSTRUCT *kb = (KBDLLHOOKSTRUCT *)lParam;
    int vk = (int)kb->vkCode;

    /* Clamp to 0-255 */
    if (vk < 0 || vk > 255)
        return CallNextHookEx(g_app.kb_hook, nCode, wParam, lParam);

    /* Settings capture mode */
    if (g_app.capturing_action >= 0 && wParam == WM_KEYDOWN) {
        wchar_t kn[32];
        if (vk == VK_ESCAPE) {
            get_key_name(g_app.keys[g_app.capturing_action], kn, 32);
            SetDlgItemTextW(g_app.hwnd_settings, IDC_KEY_BASE + g_app.capturing_action, kn);
            g_app.capturing_action = -1;
        } else {
            g_app.keys[g_app.capturing_action] = vk;
            get_key_name(vk, kn, 32);
            SetDlgItemTextW(g_app.hwnd_settings, IDC_KEY_BASE + g_app.capturing_action, kn);
            g_app.capturing_action = -1;
        }
        invalidate_all();
        return 1; /* Swallow the key press during capture */
    }

    if (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN) {
        if (!g_app.key_is_down[vk]) {
            g_app.key_is_down[vk] = 1;
            QueryPerformanceCounter(&g_app.key_down_time[vk]);

            /* Instant actions (config keys) */
            if (vk == VK_F10)                                PostMessage(g_app.hwnd_main, WM_CLOSE, 0, 0);
            else if (vk == g_app.keys[ACT_CYCLE_MAP])        PostMessage(g_app.hwnd_main, WM_USER + 100, ACT_CYCLE_MAP, 0);
            else if (vk == g_app.keys[ACT_TOGGLE_CURSED])   PostMessage(g_app.hwnd_main, WM_USER + 100, ACT_TOGGLE_CURSED, 0);
            else if (vk == g_app.keys[ACT_CYCLE_DIFFICULTY]) PostMessage(g_app.hwnd_main, WM_USER + 100, ACT_CYCLE_DIFFICULTY, 0);
            else if (vk == g_app.keys[ACT_CYCLE_VIEW])       PostMessage(g_app.hwnd_main, WM_USER + 100, ACT_CYCLE_VIEW, 0);
            else if (vk == g_app.keys[ACT_GHOST_RHYTHM])     PostMessage(g_app.hwnd_main, WM_USER + 100, ACT_GHOST_RHYTHM, 0);
        }
    }

    if (wParam == WM_KEYUP || wParam == WM_SYSKEYUP) {
        if (g_app.key_is_down[vk]) {
            g_app.key_is_down[vk] = 0;
            LARGE_INTEGER now;
            QueryPerformanceCounter(&now);
            double dur = (double)(now.QuadPart - g_app.key_down_time[vk].QuadPart) / g_app.tick_freq;
            int is_hold = (dur >= 0.4);

            if (vk == g_app.keys[ACT_HUNT]) {
                PostMessage(g_app.hwnd_main, WM_USER + 101, is_hold, 0);
            }
            else if (vk == g_app.keys[ACT_INCENSE_START]) {
                PostMessage(g_app.hwnd_main, WM_USER + 102, is_hold, 0);
            }
            else if (vk == g_app.keys[ACT_INCENSE_PAUSE]) {
                PostMessage(g_app.hwnd_main, WM_USER + 103, 0, 0);
            }
            else if (vk == g_app.keys[ACT_BPM_TAP]) {
                PostMessage(g_app.hwnd_main, WM_USER + 104, is_hold, 0);
            }
        }
    }

    return CallNextHookEx(g_app.kb_hook, nCode, wParam, lParam);
}

/* ═══════════════════════════════════════════════════════════════
 * SETTINGS DIALOG
 * ═══════════════════════════════════════════════════════════════ */

#define IDC_SAVE      2001
#define IDC_CANCEL    2002
#define IDC_RESET_DEFAULTS 2003
#define IDC_MAP_BASE  2100
#define IDC_HUNT_BASE 2200
#define IDC_KEY_BASE  2300

static LRESULT CALLBACK SettingsWndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    static int temp_map, temp_hunt;
    static int temp_keys[ACT_COUNT];

    switch (msg) {
    case WM_CREATE: {
        temp_map  = g_app.map_idx;
        temp_hunt = g_app.hunt_idx;
        for (int i = 0; i < ACT_COUNT; i++)
            temp_keys[i] = g_app.keys[i];

        int y = 14;

        /* Title */
        HWND hTitle = CreateWindowW(L"STATIC", L"\x2699  OPCIONES",
                      WS_CHILD | WS_VISIBLE | SS_CENTER,
                      0, y, 440, 24, hwnd, NULL, NULL, NULL);
        SendMessageW(hTitle, WM_SETFONT, (WPARAM)g_app.f_settings_title, TRUE);
        y += 40;

        /* Map radio buttons */
        HWND hMapLbl = CreateWindowW(L"STATIC", L"Mapa:",
                      WS_CHILD | WS_VISIBLE,
                      16, y, 60, 20, hwnd, NULL, NULL, NULL);
        SendMessageW(hMapLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        for (int i = 0; i < MAP_COUNT; i++) {
            DWORD style = WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON;
            if (i == 0) style |= WS_GROUP;
            HWND hRadio = CreateWindowW(L"BUTTON", MAP_LABELS[i], style,
                          90 + i * 110, y, 100, 20, hwnd,
                          (HMENU)(intptr_t)(IDC_MAP_BASE + i), NULL, NULL);
            SendMessageW(hRadio, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
            if (i == temp_map)
                CheckDlgButton(hwnd, IDC_MAP_BASE + i, BST_CHECKED);
        }
        y += 30;

        /* Hunt radio buttons */
        HWND hHuntLbl = CreateWindowW(L"STATIC", L"Dificultad:",
                      WS_CHILD | WS_VISIBLE,
                      16, y, 80, 20, hwnd, NULL, NULL, NULL);
        SendMessageW(hHuntLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        for (int i = 0; i < HUNT_COUNT; i++) {
            DWORD style = WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON;
            if (i == 0) style |= WS_GROUP;
            HWND hRadio = CreateWindowW(L"BUTTON", HUNT_LABELS[i], style,
                          90 + i * 110, y, 100, 20, hwnd,
                          (HMENU)(intptr_t)(IDC_HUNT_BASE + i), NULL, NULL);
            SendMessageW(hRadio, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
            if (i == temp_hunt)
                CheckDlgButton(hwnd, IDC_HUNT_BASE + i, BST_CHECKED);
        }
        y += 40;

        /* ── DURACIÓN DE CACERÍAS ───────────────────────────── */
        HWND hTimesLbl = CreateWindowW(L"STATIC", L"DURACIÓN DE CACERÍAS (SEGUNDOS)",
                      WS_CHILD | WS_VISIBLE,
                      16, y, 420, 18, hwnd, NULL, NULL, NULL);
        SendMessageW(hTimesLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        y += 24;

        // Headers
        CreateWindowW(L"STATIC", L"CHICO", WS_CHILD | WS_VISIBLE, 140, y, 70, 18, hwnd, NULL, NULL, NULL);
        CreateWindowW(L"STATIC", L"MEDIANO", WS_CHILD | WS_VISIBLE, 220, y, 70, 18, hwnd, NULL, NULL, NULL);
        CreateWindowW(L"STATIC", L"GRANDE", WS_CHILD | WS_VISIBLE, 300, y, 70, 18, hwnd, NULL, NULL, NULL);
        y += 20;

        for (int i = 0; i < HUNT_COUNT; i++) {
            HWND hRowLbl = CreateWindowW(L"STATIC", HUNT_LABELS[i],
                          WS_CHILD | WS_VISIBLE,
                          16, y + 2, 100, 20, hwnd, NULL, NULL, NULL);
            SendMessageW(hRowLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);

            for (int j = 0; j < MAP_COUNT; j++) {
                HWND hEdit = CreateWindowW(L"EDIT", L"",
                               WS_CHILD | WS_VISIBLE | WS_BORDER | ES_NUMBER | ES_CENTER,
                               130 + j * 80, y, 60, 20, hwnd,
                               (HMENU)(intptr_t)(IDC_EDIT_BASE + i * 3 + j), NULL, NULL);
                SendMessageW(hEdit, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
                SetDlgItemInt(hwnd, IDC_EDIT_BASE + i * 3 + j, g_app.hunt_matrix[i][j], FALSE);
            }
            y += 24;
        }

        // Cursed Mod
        HWND hCursedLbl = CreateWindowW(L"STATIC", L"Mod. Maldita:",
                      WS_CHILD | WS_VISIBLE,
                      16, y + 2, 100, 20, hwnd, NULL, NULL, NULL);
        SendMessageW(hCursedLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);

        HWND hCursedEdit = CreateWindowW(L"EDIT", L"",
                      WS_CHILD | WS_VISIBLE | WS_BORDER | ES_NUMBER | ES_CENTER,
                      130, y, 60, 20, hwnd,
                      (HMENU)(intptr_t)IDC_EDIT_CURSED, NULL, NULL);
        SendMessageW(hCursedEdit, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        SetDlgItemInt(hwnd, IDC_EDIT_CURSED, g_app.cursed_mod, FALSE);

        HWND hExtraLbl = CreateWindowW(L"STATIC", L"segundos extra",
                      WS_CHILD | WS_VISIBLE,
                      200, y + 2, 150, 20, hwnd, NULL, NULL, NULL);
        SendMessageW(hExtraLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        y += 40;

        // Ghost Rhythm BPM
        HWND hBpmLbl = CreateWindowW(L"STATIC", L"Ritmo Fantasma:",
                      WS_CHILD | WS_VISIBLE,
                      16, y + 2, 130, 20, hwnd, NULL, NULL, NULL);
        SendMessageW(hBpmLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);

        HWND hBpmEdit = CreateWindowW(L"EDIT", L"",
                      WS_CHILD | WS_VISIBLE | WS_BORDER | ES_NUMBER | ES_CENTER,
                      150, y, 60, 20, hwnd,
                      (HMENU)(intptr_t)IDC_EDIT_BPM, NULL, NULL);
        SendMessageW(hBpmEdit, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        SetDlgItemInt(hwnd, IDC_EDIT_BPM, g_app.ghost_bpm, FALSE);

        HWND hBpmExtraLbl = CreateWindowW(L"STATIC", L"BPM",
                      WS_CHILD | WS_VISIBLE,
                      220, y + 2, 150, 20, hwnd, NULL, NULL, NULL);
        SendMessageW(hBpmExtraLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        y += 30;

        // Ghost Rhythm Volume
        HWND hVolLbl = CreateWindowW(L"STATIC", L"Volumen General:",
                      WS_CHILD | WS_VISIBLE,
                      16, y + 2, 130, 20, hwnd, NULL, NULL, NULL);
        SendMessageW(hVolLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);

        HWND hVolEdit = CreateWindowW(L"EDIT", L"",
                      WS_CHILD | WS_VISIBLE | WS_BORDER | ES_NUMBER | ES_CENTER,
                      150, y, 60, 20, hwnd,
                      (HMENU)(intptr_t)IDC_EDIT_VOLUME, NULL, NULL);
        SendMessageW(hVolEdit, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        SetDlgItemInt(hwnd, IDC_EDIT_VOLUME, g_app.global_volume, FALSE);

        HWND hVolExtraLbl = CreateWindowW(L"STATIC", L"%",
                      WS_CHILD | WS_VISIBLE,
                      220, y + 2, 150, 20, hwnd, NULL, NULL, NULL);
        SendMessageW(hVolExtraLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        y += 40;

        /* Reset Defaults Button */
        HWND hReset = CreateWindowW(L"BUTTON", L"\x21FB  RESTABLECER TIEMPOS",
                      WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                      16, y, 200, 24, hwnd,
                      (HMENU)(intptr_t)IDC_RESET_DEFAULTS, NULL, NULL);
        SendMessageW(hReset, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);

        HWND hApply = CreateWindowW(L"BUTTON", L"\x2714  APLICAR CAMBIOS",
                      WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                      236, y, 200, 24, hwnd,
                      (HMENU)(intptr_t)IDC_APPLY, NULL, NULL);
        SendMessageW(hApply, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        y += 34;

        /* Key bindings */
        HWND hKeysLbl = CreateWindowW(L"STATIC", L"CONTROLES  \x00B7  clic para reasignar  \x00B7  ESC cancela",
                      WS_CHILD | WS_VISIBLE,
                      16, y, 420, 18, hwnd, NULL, NULL, NULL);
        SendMessageW(hKeysLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        y += 24;

        for (int i = 0; i < ACT_COUNT; i++) {
            HWND hActLbl = CreateWindowW(L"STATIC", ACTION_LABELS[i],
                          WS_CHILD | WS_VISIBLE,
                          16, y + 4, 220, 20, hwnd, NULL, NULL, NULL);
            SendMessageW(hActLbl, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
            wchar_t kn[32];
            get_key_name(g_app.keys[i], kn, 32);
            HWND hActBtn = CreateWindowW(L"BUTTON", kn,
                          WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                          260, y, 160, 24, hwnd,
                          (HMENU)(intptr_t)(IDC_KEY_BASE + i), NULL, NULL);
            SendMessageW(hActBtn, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
            y += 30;
        }
        y += 10;

        /* Save / Cancel */
        HWND hSave = CreateWindowW(L"BUTTON", L"  GUARDAR  ",
                      WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                      100, y, 110, 32, hwnd,
                      (HMENU)(intptr_t)IDC_SAVE, NULL, NULL);
        SendMessageW(hSave, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        HWND hCancel = CreateWindowW(L"BUTTON", L"  CANCELAR  ",
                      WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                      230, y, 110, 32, hwnd,
                      (HMENU)(intptr_t)IDC_CANCEL, NULL, NULL);
        SendMessageW(hCancel, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        return 0;
    }

    case WM_CTLCOLOREDIT: {
        HDC hdcEdit = (HDC)wParam;
        SetTextColor(hdcEdit, C_ACCENT);
        SetBkColor(hdcEdit, C_ROOT);
        static HBRUSH hbrEditBg = NULL;
        if (!hbrEditBg) hbrEditBg = CreateSolidBrush(C_ROOT);
        return (INT_PTR)hbrEditBg;
    }

    case WM_CTLCOLORSTATIC: {
        HDC hdcStatic = (HDC)wParam;
        SetTextColor(hdcStatic, RGB(0xdd, 0xdd, 0xff)); // Light blue text for high-end feel
        SetBkColor(hdcStatic, C_PANEL);
        static HBRUSH hbrPanel = NULL;
        if (!hbrPanel) hbrPanel = CreateSolidBrush(C_PANEL);
        return (INT_PTR)hbrPanel;
    }

    case WM_COMMAND: {
        int id = LOWORD(wParam);

        /* Map radios */
        for (int i = 0; i < MAP_COUNT; i++) {
            if (id == IDC_MAP_BASE + i) temp_map = i;
        }
        /* Hunt radios */
        for (int i = 0; i < HUNT_COUNT; i++) {
            if (id == IDC_HUNT_BASE + i) temp_hunt = i;
        }

        /* Key buttons → enter capture mode */
        for (int i = 0; i < ACT_COUNT; i++) {
            if (id == IDC_KEY_BASE + i) {
                g_app.capturing_action = i;
                SetDlgItemTextW(hwnd, IDC_KEY_BASE + i, L"[ PRESIONA ]");
            }
        }

        if (id == IDC_RESET_DEFAULTS) {
            static const int DEFAULT_HUNT_MATRIX[3][3] = {
                { 15, 30, 40 },  /* baja  */
                { 20, 40, 50 },  /* media */
                { 30, 50, 60 },  /* alta  */
            };
            for (int i = 0; i < 3; i++) {
                for (int j = 0; j < 3; j++) {
                    SetDlgItemInt(hwnd, IDC_EDIT_BASE + i * 3 + j, DEFAULT_HUNT_MATRIX[i][j], FALSE);
                }
            }
            SetDlgItemInt(hwnd, IDC_EDIT_CURSED, 20, FALSE);
            SetDlgItemInt(hwnd, IDC_EDIT_BPM, 117, FALSE);
            SetDlgItemInt(hwnd, IDC_EDIT_VOLUME, 80, FALSE);
        }

        if (id == IDC_SAVE || id == IDC_APPLY) {
            g_app.capturing_action = -1;
            g_app.map_idx  = temp_map;
            g_app.hunt_idx = temp_hunt;

            /* Save edit controls values */
            for (int i = 0; i < 3; i++) {
                for (int j = 0; j < 3; j++) {
                    BOOL trans;
                    UINT val = GetDlgItemInt(hwnd, IDC_EDIT_BASE + i * 3 + j, &trans, FALSE);
                    if (trans && val > 0) {
                        g_app.hunt_matrix[i][j] = (int)val;
                    }
                }
            }
            BOOL trans_cursed;
            UINT val_cursed = GetDlgItemInt(hwnd, IDC_EDIT_CURSED, &trans_cursed, FALSE);
            if (trans_cursed && val_cursed >= 0) {
                g_app.cursed_mod = (int)val_cursed;
            }

            BOOL trans_bpm;
            UINT val_bpm = GetDlgItemInt(hwnd, IDC_EDIT_BPM, &trans_bpm, FALSE);
            if (trans_bpm && val_bpm > 0) {
                g_app.ghost_bpm = (int)val_bpm;
                g_app.ghost_interval = 60.0 / g_app.ghost_bpm;
            }

            BOOL trans_vol;
            UINT val_vol = GetDlgItemInt(hwnd, IDC_EDIT_VOLUME, &trans_vol, FALSE);
            if (trans_vol && val_vol <= 100) {
                g_app.global_volume = (int)val_vol;
            }

            if (g_app.ghost_active) {
                PlaySoundA(NULL, NULL, 0);
                generate_beep_wav(120, 30, g_app.global_volume, 45.0);
            }

            recalc();
            save_config();
            invalidate_all();
            if (id == IDC_SAVE) {
                DestroyWindow(hwnd);
            }
        }
        if (id == IDC_CANCEL) {
            g_app.capturing_action = -1;
            /* Restore keys */
            for (int i = 0; i < ACT_COUNT; i++)
                g_app.keys[i] = temp_keys[i];
            DestroyWindow(hwnd);
        }
        return 0;
    }

    case WM_DESTROY:
        g_app.hwnd_settings = NULL;
        g_app.capturing_action = -1;
        return 0;

    case WM_CLOSE:
        /* Same as cancel */
        g_app.capturing_action = -1;
        for (int i = 0; i < ACT_COUNT; i++)
            g_app.keys[i] = temp_keys[i];
        DestroyWindow(hwnd);
        return 0;
    }

    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

static void open_settings(void) {
    if (g_app.hwnd_settings && IsWindow(g_app.hwnd_settings)) {
        SetForegroundWindow(g_app.hwnd_settings);
        return;
    }

    static int registered = 0;
    if (!registered) {
        WNDCLASSEXW wc = {0};
        wc.cbSize        = sizeof(wc);
        wc.lpfnWndProc   = SettingsWndProc;
        wc.hInstance      = GetModuleHandle(NULL);
        wc.hbrBackground = CreateSolidBrush(C_PANEL);
        wc.lpszClassName = L"NefaHUBSettings";
        wc.hCursor       = LoadCursor(NULL, IDC_ARROW);
        RegisterClassExW(&wc);
        registered = 1;
    }

    g_app.hwnd_settings = CreateWindowExW(
        WS_EX_TOPMOST,
        L"NefaHUBSettings",
        L"Opciones \x2014 NefaHUB ",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU,
        CW_USEDEFAULT, CW_USEDEFAULT,
        460, 780,
        g_app.hwnd_main,
        NULL, GetModuleHandle(NULL), NULL);

    ShowWindow(g_app.hwnd_settings, SW_SHOW);
    UpdateWindow(g_app.hwnd_settings);
}

/* ═══════════════════════════════════════════════════════════════
 * MAIN WINDOW PROC
 * ═══════════════════════════════════════════════════════════════ */

/* Button IDs */
#define IDC_BTN_SETTINGS 3001

static LRESULT CALLBACK MainWndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {

    case WM_CREATE:
        SetTimer(hwnd, TIMER_TICK, 50, NULL);

        HWND hSettingsBtn = CreateWindowW(L"BUTTON", L"\x2699 OPCIONES",
                      WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                      30, 320, 140, 28, hwnd,
                      (HMENU)(intptr_t)IDC_BTN_SETTINGS, NULL, NULL);
        SendMessageW(hSettingsBtn, WM_SETFONT, (WPARAM)g_app.f_settings_btn, TRUE);
        return 0;

    case WM_TIMER:
        if (wParam == TIMER_TICK)
            tick();
        return 0;

    case WM_PAINT:
        paint_main(hwnd);
        return 0;

    case WM_ERASEBKGND:
        return 1; /* prevent flicker */

    case WM_COMMAND:
        if (LOWORD(wParam) == IDC_BTN_SETTINGS)
            open_settings();
        return 0;

    /* Custom messages from keyboard hook */
    case WM_USER + 100: { /* Instant config action */
        int act = (int)wParam;
        switch (act) {
            case ACT_CYCLE_MAP:        cycle_map();        break;
            case ACT_TOGGLE_CURSED:    toggle_cursed();    break;
            case ACT_CYCLE_DIFFICULTY: cycle_difficulty();  break;
            case ACT_CYCLE_VIEW:       cycle_view();       break;
            case ACT_GHOST_RHYTHM:     toggle_ghost_rhythm(); break;
        }
        return 0;
    }

    case WM_USER + 101: /* Hunt key released */
        if (wParam) reset_hunt();
        else        start_hunt();
        return 0;

    case WM_USER + 102: /* Incense start key released */
        if (wParam) reset_incense();
        else        start_incense();
        return 0;

    case WM_USER + 103: /* Incense pause */
        pause_incense();
        return 0;

    case WM_USER + 104: /* BPM tap key released */
        if (wParam) reset_bpm();
        else        on_bpm_tap();
        return 0;

    /* Dragging (no title bar) */
    case WM_LBUTTONDOWN:
        if ((int)(short)HIWORD(lParam) < 20 || 1) {
            ReleaseCapture();
            SendMessage(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, lParam);
        }
        return 0;

    case WM_DESTROY:
        save_config();
        PostQuitMessage(0);
        return 0;
    }

    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

/* ═══════════════════════════════════════════════════════════════
 * OVERLAY WINDOW PROC
 * ═══════════════════════════════════════════════════════════════ */

static LRESULT CALLBACK OverlayWndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
    case WM_PAINT:
        paint_overlay(hwnd);
        return 0;
    case WM_ERASEBKGND:
        return 1;
    }
    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

/* ═══════════════════════════════════════════════════════════════
 * ENTRY POINT
 * ═══════════════════════════════════════════════════════════════ */

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmdLine, int cmdShow) {
    (void)hPrev; (void)cmdLine;

    /* DPI awareness */
    {
        typedef HRESULT (WINAPI *SetDPI_t)(int);
        HMODULE shcore = LoadLibraryW(L"shcore.dll");
        if (shcore) {
            SetDPI_t fn = (SetDPI_t)GetProcAddress(shcore, "SetProcessDpiAwareness");
            if (fn) fn(1);
            FreeLibrary(shcore);
        }
    }

    /* Performance counter frequency */
    LARGE_INTEGER freq;
    QueryPerformanceFrequency(&freq);
    g_app.tick_freq = (double)freq.QuadPart;
    QueryPerformanceCounter(&g_app.last_tick);

    /* Init state */
    g_app.capturing_action = -1;
    load_config();

    /* Create fonts */
    g_app.f_clock_main    = create_font(L"Consolas", 46, 1);
    g_app.f_clock_ov      = create_font(L"Consolas", 42, 1);
    g_app.f_status_main   = create_font(L"Impact",   18, 0);
    g_app.f_status_ov     = create_font(L"Consolas", 10, 1);
    g_app.f_incense       = create_font(L"Consolas", 20, 1);
    g_app.f_incense_ov    = create_font(L"Consolas", 42, 1);
    g_app.f_incense_ico   = create_font(L"Segoe UI Emoji", 34, 0);
    g_app.f_config_lbl    = create_font(L"Consolas",  8, 1);
    g_app.f_config_val    = create_font(L"Consolas",  9, 1);
    g_app.f_ref_lbl       = create_font(L"Consolas",  7, 1);
    g_app.f_ref_val       = create_font(L"Consolas", 12, 1);
    g_app.f_cfg_hint      = create_font(L"Consolas", 18, 1);
    g_app.f_total         = create_font(L"Consolas", 10, 1);
    g_app.f_settings_title = create_font(L"Consolas", 13, 1);
    g_app.f_settings_btn  = create_font(L"Consolas",  8, 1);

    /* Register main window class */
    WNDCLASSEXW wc = {0};
    wc.cbSize        = sizeof(wc);
    wc.lpfnWndProc   = MainWndProc;
    wc.hInstance      = hInst;
    wc.hbrBackground = CreateSolidBrush(C_ROOT);
    wc.lpszClassName = L"NefaHUBMain";
    wc.hCursor       = LoadCursor(NULL, IDC_ARROW);
    RegisterClassExW(&wc);

    /* Register overlay window class */
    WNDCLASSEXW wc2 = {0};
    wc2.cbSize        = sizeof(wc2);
    wc2.lpfnWndProc   = OverlayWndProc;
    wc2.hInstance      = hInst;
    wc2.hbrBackground = CreateSolidBrush(C_CHROMA);
    wc2.lpszClassName = L"NefaHUBOverlay";
    wc2.hCursor       = LoadCursor(NULL, IDC_ARROW);
    RegisterClassExW(&wc2);

    /* Create main window */
    g_app.hwnd_main = CreateWindowExW(
        WS_EX_TOPMOST,
        L"NefaHUBMain",
        MAIN_TITLE,
        WS_POPUP,
        g_app.win_x, g_app.win_y,
        MAIN_W, MAIN_H,
        NULL, NULL, hInst, NULL);

    /* Create overlay (hidden initially) */
    g_app.hwnd_overlay = CreateWindowExW(
        WS_EX_TOPMOST | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW,
        L"NefaHUBOverlay",
        OVERLAY_TITLE,
        WS_POPUP | WS_VISIBLE,
        g_app.win_x, g_app.win_y,
        OV_W, OV_H,
        NULL, NULL, hInst, NULL);

    /* Set chroma key for overlay */
    SetLayeredWindowAttributes(g_app.hwnd_overlay, C_CHROMA, 0, LWA_COLORKEY);

    /* Init game state */
    recalc();
    g_app.view_mode = 2;

    /* Install low-level keyboard hook */
    g_app.kb_hook = SetWindowsHookExW(WH_KEYBOARD_LL, LowLevelKBProc, hInst, 0);

    /* Welcome sound */
    beep_async(SND_WELCOME);

    /* Message loop */
    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    /* Cleanup */
    if (g_app.kb_hook) UnhookWindowsHookEx(g_app.kb_hook);

    DeleteObject(g_app.f_clock_main);
    DeleteObject(g_app.f_clock_ov);
    DeleteObject(g_app.f_status_main);
    DeleteObject(g_app.f_status_ov);
    DeleteObject(g_app.f_incense);
    DeleteObject(g_app.f_incense_ov);
    DeleteObject(g_app.f_incense_ico);
    DeleteObject(g_app.f_config_lbl);
    DeleteObject(g_app.f_config_val);
    DeleteObject(g_app.f_ref_lbl);
    DeleteObject(g_app.f_ref_val);
    DeleteObject(g_app.f_cfg_hint);
    DeleteObject(g_app.f_total);
    DeleteObject(g_app.f_settings_title);
    DeleteObject(g_app.f_settings_btn);

    return (int)msg.wParam;
}
