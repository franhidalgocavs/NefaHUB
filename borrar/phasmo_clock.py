import os, json, time, ctypes, threading
import tkinter as tk
import winsound, keyboard

# ── Win32 constants ───────────────────────────────────────────
GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

# ── Titles / config file ──────────────────────────────────────
MAIN_TITLE    = "PhasmoClock"
OVERLAY_TITLE = "PhasmoClockOV"
CONFIG_FILE   = "phasmo_config.json"

# ── Game timing constants ─────────────────────────────────────
MAP_CYCLE  = ["chico",  "mediano", "grande"]
MAP_LABELS = {"chico": "CHICO", "mediano": "MEDIANO", "grande": "GRANDE"}

HUNT_CYCLE  = ["baja",  "media", "alta"]
HUNT_LABELS = {"baja": "BAJA", "media": "MEDIA", "alta": "ALTA"}

HUNT_MATRIX = {
    "baja":  {"chico": 15, "mediano": 30, "grande": 40},
    "media": {"chico": 20, "mediano": 40, "grande": 50},
    "alta":  {"chico": 30, "mediano": 50, "grande": 60}
}

CURSED_MOD       = 20


# ── Color palette ─────────────────────────────────────────────
C_ROOT   = "#0d0f1a"
C_PANEL  = "#12141f"
C_BLOCK  = "#181a28"
C_ACCENT = "#00ffcc"
C_DIM    = "#555577"
C_RED    = "#ff3333"
C_ORANGE = "#ff9f43"
C_GOLD   = "#f4d03f"
C_PURPLE = "#d300ff"
C_BLUE   = "#00bcff"
C_GREEN  = "#2ecc71"
C_CHROMA = "#010101"   # transparent key for overlay

# ── Default key bindings ──────────────────────────────────────
DEFAULT_KEYS = {
    "incense_start":    "1",
    "incense_pause":    "2",
    "hunt":             "3",
    "cycle_map":        "f1",
    "toggle_cursed":    "f2",
    "cycle_difficulty": "f3",
    "cycle_view":       "f9",
}

ACTION_LABELS = {
    "incense_start":    "Iniciar Incienso",
    "incense_pause":    "Pausar Incienso",
    "hunt":             "Cace\u00eda / Reset (largo)",
    "cycle_map":        "Ciclar Mapa",
    "toggle_cursed":    "Modo Maldita",
    "cycle_difficulty": "Ciclar Dificultad",
    "cycle_view":       "Cambiar Vista",
}

# ── Font tokens ────────────────────────────────────────────────
F_CLOCK_MAIN  = ("Consolas", 46, "bold")   # reloj cacería (main)
F_CLOCK_OV    = ("Consolas", 42, "bold")   # reloj cacería (overlay)
F_STATUS_MAIN = ("Impact",   18)            # estado cacería (main)
F_STATUS_OV   = ("Consolas", 10, "bold")   # estado cacería (overlay)
F_INCENSE     = ("Consolas", 20, "bold")   # incienso (main)
F_INCENSE_OV  = ("Consolas", 42, "bold")   # incienso (overlay)
F_INCENSE_ICO = ("Consolas", 34)            # ícono 💨 (overlay)
F_CONFIG_LBL  = ("Consolas",  8, "bold")
F_CONFIG_VAL  = ("Consolas",  9, "bold")
F_REF_LBL     = ("Consolas",  7, "bold")
F_REF_VAL     = ("Consolas", 12, "bold")

# ── Overlay geometry ───────────────────────────────────────────
OV_W, OV_H = 420, 280


# ═════════════════════════════════════════════════════════════
class PhasmoClockApp:
# ═════════════════════════════════════════════════════════════

    def __init__(self, root):
        self.root = root
        self.root.title(MAIN_TITLE)
        self.root.resizable(False, False)

        # ── Game state ────────────────────────────────────────
        self.map_idx   = 1        # default: mediano
        self.is_cursed = False
        self.hunt_idx  = 1        # default: mediana

        self.hunt_active  = False
        self.hunt_time    = 0.0
        self.hunt_total   = 0.0
        self.hunt_ref     = None

        self.cooldown_active = False
        self.cooldown_time   = 0.0

        self.incense_active = False
        self.incense_paused = False
        self.incense_was_paused = False
        self.incense_time   = 0.0

        self.last_tick_time = time.time()

        # ── View state ────────────────────────────────────────
        # 0 = Normal (config + HUD)
        # 2 = Super Minimalista (transparent overlay Toplevel)
        self.view_mode = 0
        self.hotkeys_registered = False
        self.capturing_action   = None
        self._capture_callback  = None

        # ── Load saved config ─────────────────────────────────
        wx, wy = self._load_config()

        # ── Build main window ─────────────────────────────────
        self.root.config(bg=C_ROOT)
        self.root.wm_attributes("-topmost", True)
        self.root.geometry(f"540x400+{wx}+{wy}")
        self._build_main_ui()

        # ── Build overlay (separate Toplevel, always transparent) ──
        self._build_overlay(wx, wy)

        # ── Init ──────────────────────────────────────────────
        self._setup_hotkeys()
        self._recalc()
        self._tick()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._beep_thread("welcome")

    # ══════════════════════════════════════════════════════════
    # PERSISTENCE
    # ══════════════════════════════════════════════════════════
    def _load_config(self):
        self.hunt_matrix = {hk: {mk: float(HUNT_MATRIX[hk][mk]) for mk in MAP_CYCLE} for hk in HUNT_CYCLE}
        self.cursed_mod = 20.0
        try:
            with open(CONFIG_FILE) as f:
                d = json.load(f)
            self.keys     = {**DEFAULT_KEYS, **d.get("keys", {})}
            self.map_idx  = d.get("default_map_idx",  self.map_idx)
            self.hunt_idx = d.get("default_hunt_idx", self.hunt_idx)
            self.cursed_mod = d.get("cursed_mod", self.cursed_mod)
            
            # Load flat keys first for compatibility
            for hk in HUNT_CYCLE:
                for mk in MAP_CYCLE:
                    k = f"time_{hk}_{mk}"
                    if k in d:
                        try:
                            self.hunt_matrix[hk][mk] = float(d[k])
                        except ValueError:
                            pass
            
            # Override with nested hunt_matrix if present
            if "hunt_matrix" in d:
                loaded = d["hunt_matrix"]
                for hk in HUNT_CYCLE:
                    if hk in loaded:
                        for mk in MAP_CYCLE:
                            if mk in loaded[hk]:
                                try:
                                    self.hunt_matrix[hk][mk] = float(loaded[hk][mk])
                                except ValueError:
                                    pass
            return d.get("window_x", 100), d.get("window_y", 100)
        except:
            self.keys = dict(DEFAULT_KEYS)
            return 100, 100

    def _save_config(self):
        try:
            w = self.overlay if self.view_mode == 2 else self.root
            d = {
                "window_x":        w.winfo_x(),
                "window_y":        w.winfo_y(),
                "default_map_idx":  self.map_idx,
                "default_hunt_idx": self.hunt_idx,
                "keys":             self.keys,
                "hunt_matrix":      self.hunt_matrix,
                "cursed_mod":       self.cursed_mod,
            }
            # Write flat keys too for C compatibility
            for hk in HUNT_CYCLE:
                for mk in MAP_CYCLE:
                    d[f"time_{hk}_{mk}"] = self.hunt_matrix[hk][mk]
            
            with open(CONFIG_FILE, "w") as f:
                json.dump(d, f, indent=2)
        except:
            pass

    # ══════════════════════════════════════════════════════════
    # SOUND
    # ══════════════════════════════════════════════════════════
    def _beep(self, f, ms):
        try: winsound.Beep(f, ms)
        except: pass

    def _beep_thread(self, action):
        def run():
            if   action == "welcome":       self._beep(600,80);  self._beep(900,100); self._beep(1200,130)
            elif action == "hunt_start":    self._beep(880,130); self._beep(880,130)
            elif action == "incense_start": self._beep(523,80);  self._beep(659,80);  self._beep(784,120)
            elif action == "safe":          self._beep(1047,100);self._beep(1318,100);self._beep(1568,180)
            elif action == "incense_done":  self._beep(784,100); self._beep(659,100); self._beep(523,150)
            elif action == "config":        self._beep(750,80)
            elif action == "cursed_on":     self._beep(880,80);  self._beep(660,120)
            elif action == "cursed_off":    self._beep(660,80);  self._beep(880,120)
            elif action == "view":          self._beep(800,60)
        threading.Thread(target=run, daemon=True).start()

    # ══════════════════════════════════════════════════════════
    # HOTKEYS
    # ══════════════════════════════════════════════════════════
    def _setup_hotkeys(self):
        if self.hotkeys_registered:
            return
            
        self.key_press_times = {}
        
        def match_key(ev, key_name):
            if not key_name:
                return False
            n = (ev.name or "").lower()
            if n == key_name.lower() or n == f"numpad {key_name.lower()}":
                return True
            try:
                sc_list = keyboard.key_to_scan_codes(key_name)
                if ev.scan_code in sc_list:
                    return True
            except:
                pass
            return False
        
        def on_key(ev):
            n = (ev.name or "").lower()
            sc = ev.scan_code
            s = self.root.after

            # ── Capture mode (settings dialog) ────────────────────
            if self.capturing_action:
                if ev.event_type == keyboard.KEY_DOWN:
                    action = self.capturing_action
                    cb     = self._capture_callback
                    self.capturing_action  = None
                    self._capture_callback = None
                    if n != "escape":
                        self.keys[action] = n
                        if cb: s(0, lambda a=action, k=n: cb(a, k))
                    else:
                        if cb: s(0, lambda a=action: cb(a, None))
                return

            if ev.event_type == keyboard.KEY_DOWN:
                if sc not in self.key_press_times:
                    self.key_press_times[sc] = time.time()
                    if   match_key(ev, self.keys["cycle_map"]):        s(0, self._cycle_map)
                    elif match_key(ev, self.keys["toggle_cursed"]):     s(0, self._toggle_cursed)
                    elif match_key(ev, self.keys["cycle_difficulty"]): s(0, self._cycle_hunt_duration)
                    elif match_key(ev, self.keys["cycle_view"]):       s(0, self._cycle_view)
                return

            if ev.event_type == keyboard.KEY_UP:
                press_time = self.key_press_times.pop(sc, None)
                if not press_time:
                    return

                duration = time.time() - press_time
                is_hold  = duration >= 0.4

                if match_key(ev, self.keys["hunt"]):
                    if is_hold: s(0, self._reset_hunt)
                    else:       s(0, self._start_hunt)

                elif match_key(ev, self.keys["incense_start"]):
                    if is_hold: s(0, self._reset_incense)
                    else:       s(0, self._start_incense)

                elif match_key(ev, self.keys["incense_pause"]):
                    s(0, self._pause_incense)

        keyboard.hook(on_key)
        self.hotkeys_registered = True

    # ══════════════════════════════════════════════════════════
    # CONFIG LOGIC
    # ══════════════════════════════════════════════════════════
    def _cycle_map(self):
        if self.cooldown_active:
            return
        old_total = self.hunt_total
        self.map_idx = (self.map_idx + 1) % len(MAP_CYCLE)
        self._beep_thread("config")
        self._recalc()
        
        if self.hunt_active:
            diff = self.hunt_total - old_total
            self.hunt_time += diff

    def _toggle_cursed(self):
        self.is_cursed = not self.is_cursed
        self._beep_thread("cursed_on" if self.is_cursed else "cursed_off")
        
        if self.hunt_active:
            if self.is_cursed:
                self.hunt_time += self.cursed_mod
            else:
                self.hunt_time -= self.cursed_mod
            self._recalc()
            color = C_PURPLE if self.is_cursed else C_RED
            self._set_status("⚠ CACERÍA ⚠", color)
        elif self.cooldown_active:
            if self.is_cursed:
                self.cooldown_time -= self.cursed_mod
            else:
                self.cooldown_time += self.cursed_mod
            self._recalc()
        else:
            self._recalc()

    def _cycle_hunt_duration(self):
        if self.cooldown_active:
            return
        old_total = self.hunt_total
        self.hunt_idx = (self.hunt_idx + 1) % len(HUNT_CYCLE)
        self._beep_thread("config")
        self._recalc()
        
        if self.hunt_active:
            diff = self.hunt_total - old_total
            self.hunt_time += diff

    def _recalc(self):
        mk = MAP_CYCLE[self.map_idx]
        hk = HUNT_CYCLE[self.hunt_idx]
        base_time = self.hunt_matrix[hk][mk]
        self.hunt_total = float(base_time + (self.cursed_mod if self.is_cursed else 0))

        self.lbl_map_val.config(text=MAP_LABELS[mk])
        self.lbl_curse_val.config(
            text=f"MALDITA 💀  +{int(self.cursed_mod)}s" if self.is_cursed else "NORMAL      +0s",
            fg=C_PURPLE if self.is_cursed else C_BLUE)
        self.lbl_hunt_val.config(text=HUNT_LABELS[hk])
        self.lbl_total.config(text=f"TOTAL: {int(self.hunt_total)}s")

        cfg_letters = f"[{mk[0].upper()}{hk[0].upper()}]"
        self.lbl_hunt_cfg.config(text=cfg_letters)
        self.ov_cfg_hint.config(text=cfg_letters)

        if not self.hunt_active and not self.cooldown_active:
            self.hunt_time = self.hunt_total
            self._render_clock(self.hunt_time, state="idle", total=self.hunt_total)

    # ══════════════════════════════════════════════════════════
    # TIMER ACTIONS
    # ══════════════════════════════════════════════════════════
    # ── Render helpers ────────────────────────────────────────
    def _set_status(self, text, color):
        """Update status label on both main window and overlay."""
        self.lbl_status.config(text=text, fg=color)
        self.ov_status.config(text=text, fg=color)

    def _render_incense(self, text, color):
        """Update all incense widgets on both surfaces."""
        self.lbl_incense_clock.config(text=text, fg=color)
        self.lbl_incense_status.config(fg=color)
        self.ov_incense.config(text=text, fg=color)
        self.ov_incense_lbl.config(fg=color)

    def _incense_color(self):
        """Rojo 0-5s, 20-25s y 60-90s."""
        t = self.incense_time
        if t < 5.0 or (20.0 <= t < 25.0) or (60.0 <= t < 90.0):
            return C_RED
        return C_ACCENT

    # ─────────────────────────────────────────────────────────
    def _start_hunt(self):
        if self.hunt_active:
            self.hunt_time = 0.0
            self.hunt_active = False
            self.cooldown_active = True
            self.cooldown_time = 0.0
            self.hunt_ref = self.hunt_total
            self._update_ref()
            self._beep_thread("safe")
            self._set_status("ENFRIAMIENTO", C_BLUE)
            self._render_clock(0.0, state="cooldown")
            return

        self.hunt_active = True
        self.hunt_time   = self.hunt_total
        self.cooldown_active = False
        self._beep_thread("hunt_start")
        color = C_PURPLE if self.is_cursed else C_RED
        self._set_status("⚠ CACERÍA ⚠", color)

    def _reset_hunt(self):
        self.hunt_active = False
        self.cooldown_active = False
        self.hunt_time = self.hunt_total
        self._beep_thread("safe")
        self._set_status("SEGURO", C_ACCENT)
        self._render_clock(self.hunt_time, state="idle", total=self.hunt_total)

    def _start_incense(self):
        if self.incense_active:
            # Si está pausado o fue pausado: siempre reiniciar (sin importar el tiempo)
            if self.incense_paused or getattr(self, "incense_was_paused", False):
                self.incense_time   = 0.0
                self.incense_paused = False
                self.incense_was_paused = False
                self._beep_thread("incense_start")
                col = self._incense_color()
                self.lbl_incense_status.config(text="🔥 INCIENSO", fg=col)
                self._render_incense("00:00.0", col)
                return
            if self.incense_time < 60.0:
                return          # bloqueado durante el primer minuto (si no está pausado o fue pausado)
            # Después del minuto: REINICIAR (no detener)
            self.incense_time   = 0.0
            self.incense_paused = False
            self.incense_was_paused = False
            self._beep_thread("incense_start")
            col = self._incense_color()
            self.lbl_incense_status.config(text="🔥 INCIENSO", fg=col)
            self._render_incense("00:00.0", col)
            return
        self.incense_active = True
        self.incense_paused = False
        self.incense_was_paused = False
        self.incense_time   = 0.0
        self._beep_thread("incense_start")
        col = self._incense_color()
        self.lbl_incense_status.config(text="🔥 INCIENSO", fg=col)
        self._render_incense("00:00.0", col)

    def _reset_incense(self):
        self.incense_active = False
        self.incense_paused = False
        self.incense_was_paused = False
        self.incense_time = 0.0
        self._beep_thread("incense_done")
        self.lbl_incense_status.config(text="INCIENSO LISTO", fg=C_ACCENT)
        self._render_incense("00:00.0", C_ACCENT)
        self.ov_incense.config(text="LISTO")

    def _pause_incense(self):
        if not self.incense_active:
            return
        self.incense_paused = not self.incense_paused
        if self.incense_paused:
            self.incense_was_paused = True
        self._beep_thread("config")
        if self.incense_paused:
            self.lbl_incense_status.config(text="⏸ PAUSADO", fg=C_ORANGE)
        else:
            col = self._incense_color()
            self.lbl_incense_status.config(text="🔥 INCIENSO", fg=col)

    # ══════════════════════════════════════════════════════════
    # MAIN TICK LOOP
    # ══════════════════════════════════════════════════════════
    def _tick(self):
        now = time.time()
        dt = now - self.last_tick_time
        self.last_tick_time = now

        if self.hunt_active:
            self.hunt_time -= dt
            if self.hunt_time <= 0:
                excess = abs(self.hunt_time)
                self.hunt_time   = 0.0
                self.hunt_active = False
                
                if excess >= 25.0:
                    self.cooldown_active = False
                    self.hunt_time = self.hunt_total
                    self._beep_thread("safe")
                    self._set_status("SEGURO", C_ACCENT)
                    self._render_clock(self.hunt_time, state="idle", total=self.hunt_total)
                else:
                    self.cooldown_active = True
                    self.cooldown_time = excess
                    self.hunt_ref    = self.hunt_total
                    self._update_ref()
                    self._beep_thread("safe")
                    self._set_status("ENFRIAMIENTO", C_BLUE)
                    self._render_clock(self.cooldown_time, state="cooldown")
            else:
                self._render_clock(self.hunt_time, state="hunt")
        elif self.cooldown_active:
            self.cooldown_time += dt
            if self.cooldown_time >= 25.0:
                self.cooldown_active = False
                self.cooldown_time = 25.0
                self._set_status("SEGURO", C_ACCENT)
                self.hunt_time = self.hunt_total
                self._render_clock(self.hunt_time, state="idle", total=self.hunt_total)
            else:
                self._render_clock(self.cooldown_time, state="cooldown")

        if self.incense_active and not self.incense_paused:
            self.incense_time += dt
            m, s, ms = int(self.incense_time // 60), int(self.incense_time % 60), int((self.incense_time * 10) % 10)
            self._render_incense(f"{m:02d}:{s:02d}.{ms}", self._incense_color())

        self.root.after(50, self._tick)

    def _render_clock(self, t, state="idle", total=None):
        sign = "-" if t < 0 else ""
        abs_t = abs(t)
        m, s, ms = int(abs_t//60), int(abs_t%60), int((abs_t*10)%10)
        txt = f"{sign}{m:02d}:{s:02d}.{ms}"
        
        if state == "idle":
            fg = C_PURPLE if self.is_cursed else C_DIM
        elif state == "hunt":
            if self.is_cursed:
                fg = C_PURPLE
            else:
                fg = C_RED if int(time.time()*3) % 2 == 0 else C_ORANGE
        elif state == "cooldown":
            if t < 0 and self.is_cursed:
                fg = C_PURPLE
            elif t >= 20.0:
                fg = C_RED
            else:
                fg = C_BLUE
            
        self.lbl_hunt_clock.config(text=txt, fg=fg)
        self.ov_clock.config(text=txt, fg=fg)

        w = self.canvas_bar.winfo_width() or 300

        if state == "hunt":
            pct = max(0, t / self.hunt_total) if self.hunt_total > 0 else 0
            self.canvas_bar.coords(self.bar_rect, 0, 0, int(w * pct), 8)
            if self.is_cursed:
                col = C_PURPLE
            else:
                col = C_RED if pct > 0.6 else C_ORANGE if pct > 0.3 else C_ACCENT
            self.canvas_bar.itemconfig(self.bar_rect, fill=col)
        elif state == "cooldown":
            pct = min(1.0, max(0, t / 25.0))
            self.canvas_bar.coords(self.bar_rect, 0, 0, int(w * pct), 8)
            col = C_RED if t >= 20.0 else C_BLUE
            self.canvas_bar.itemconfig(self.bar_rect, fill=col)
        else: # idle
            if total is None:
                total = self.hunt_total
            pct = min(1.0, max(0, t / total)) if total > 0 else 0
            self.canvas_bar.coords(self.bar_rect, 0, 0, int(w * pct), 8)
            self.canvas_bar.itemconfig(self.bar_rect, fill="#2a2a3a")

    def _update_ref(self):
        if self.hunt_ref is None:
            self.lbl_ref_val.config(text="--:--.-", fg=C_DIM)
        else:
            m, s, ms = int(self.hunt_ref//60), int(self.hunt_ref%60), int((self.hunt_ref*10)%10)
            self.lbl_ref_val.config(text=f"{m:02d}:{s:02d}.{ms}", fg=C_GOLD)

    # ══════════════════════════════════════════════════════════
    # BUILD MAIN WINDOW UI
    # ══════════════════════════════════════════════════════════
    def _build_main_ui(self):
        root_f = tk.Frame(self.root, bg=C_ROOT)
        root_f.pack(fill="both", expand=True)

        # LEFT – Config panel
        self.cfg_panel = tk.Frame(root_f, bg=C_PANEL)
        self.cfg_panel.pack(side="left", fill="y", padx=(10,4), pady=10, ipadx=10, ipady=8)

        tk.Label(self.cfg_panel, text="CONFIGURACIÓN",
                 font=("Consolas",10,"bold"), bg=C_PANEL, fg=C_ACCENT).pack(pady=(8,6))

        self._cfg_row("F1  MAPA:", "lbl_map_val",   "#ffffff")
        self._cfg_row("F2  MODO:", "lbl_curse_val", C_BLUE)
        self._cfg_row("F3  DIF:",  "lbl_hunt_val",  "#ffffff")

        tk.Frame(self.cfg_panel, bg="#222438", height=1).pack(fill="x", padx=8, pady=8)

        self.lbl_total = tk.Label(self.cfg_panel, text="TOTAL: --s",
                                  font=("Consolas",10,"bold"), bg=C_PANEL, fg="#66fcf1")
        self.lbl_total.pack(pady=2)

        tk.Frame(self.cfg_panel, bg="#222438", height=1).pack(fill="x", padx=8, pady=8)

        self.lbl_hotkey_hint = tk.Label(self.cfg_panel,
                 text="", font=("Consolas", 8), bg=C_PANEL, fg="#44475a", justify="left")
        self.lbl_hotkey_hint.pack(padx=8, pady=4)
        self._refresh_hotkey_hint()

        tk.Button(self.cfg_panel, text="⚙ OPCIONES",
                  font=("Consolas", 8, "bold"), bg=C_ROOT, fg="#555577",
                  relief="flat", cursor="hand2",
                  activebackground=C_BLOCK, activeforeground=C_ACCENT,
                  command=self._open_settings).pack(pady=(2, 8))

        # RIGHT – HUD panel
        self.hud_panel = tk.Frame(root_f, bg=C_ROOT)
        self.hud_panel.pack(side="right", fill="both", expand=True, padx=(4,10), pady=10)

        # Incense block (arriba)
        ib = tk.Frame(self.hud_panel, bg=C_BLOCK)
        ib.pack(fill="x", pady=(0,6))

        inc_row = tk.Frame(ib, bg=C_BLOCK)
        inc_row.pack(fill="x", padx=10, pady=(8,8))

        self.lbl_incense_status = tk.Label(inc_row, text="INCIENSO [1]",
                                           font=F_CONFIG_VAL, bg=C_BLOCK, fg=C_DIM)
        self.lbl_incense_status.pack(side="left")

        self.lbl_incense_clock = tk.Label(inc_row, text="00:00.0",
                                          font=F_INCENSE, bg=C_BLOCK, fg=C_DIM)
        self.lbl_incense_clock.pack(side="right")

        # Hunt block (abajo)
        hb = tk.Frame(self.hud_panel, bg=C_BLOCK)
        hb.pack(fill="x")

        top_row = tk.Frame(hb, bg=C_BLOCK)
        top_row.pack(fill="x", padx=10, pady=(8,0))

        self.lbl_status = tk.Label(top_row, text="SEGURO",
                                   font=F_STATUS_MAIN, bg=C_BLOCK, fg=C_ACCENT)
        self.lbl_status.pack(side="left")

        ref_f = tk.Frame(top_row, bg=C_BLOCK)
        ref_f.pack(side="right")
        tk.Label(ref_f, text="ÚLTIMO", font=F_REF_LBL, bg=C_BLOCK, fg="#333355").pack(anchor="e")
        self.lbl_ref_val = tk.Label(ref_f, text="--:--.-",
                                    font=F_REF_VAL, bg=C_BLOCK, fg=C_DIM)
        self.lbl_ref_val.pack(anchor="e")

        # Clock + bar wrapper
        self.hunt_clock_frame = tk.Frame(hb, bg=C_BLOCK)
        self.hunt_clock_frame.pack(fill="x")

        # Inner frame to keep the clock centered
        clk_inner = tk.Frame(self.hunt_clock_frame, bg=C_BLOCK)
        clk_inner.pack(pady=(0,4))

        self.lbl_hunt_cfg = tk.Label(clk_inner, text="[--]", font=("Consolas", 18, "bold"), bg=C_BLOCK, fg="#44475a")
        self.lbl_hunt_cfg.pack(side="left", padx=(0, 6), anchor="s", pady=(0,8))

        self.lbl_hunt_clock = tk.Label(clk_inner, text="00:00.0",
                                       font=F_CLOCK_MAIN, bg=C_BLOCK, fg="#555577")
        self.lbl_hunt_clock.pack(side="left")

        self.canvas_bar = tk.Canvas(self.hunt_clock_frame, height=8, bg=C_ROOT, highlightthickness=0)
        self.canvas_bar.pack(fill="x", padx=10, pady=(0,8))
        self.bar_rect = self.canvas_bar.create_rectangle(0, 0, 0, 8, fill="#2a2a3a", width=0)


    def _refresh_hotkey_hint(self):
        """Update the key-hint label in the config panel from current bindings."""
        k = self.keys
        lines = [
            f"[{k['incense_start'].upper()}]  Incienso",
            f"[{k['incense_pause'].upper()}]  Pausa",
            f"[{k['hunt'].upper()}]  Cace\u00eda",
            f"[{k['cycle_view'].upper()}] Vista",
        ]
        self.lbl_hotkey_hint.config(text="\n".join(lines))

    # ══════════════════════════════════════════════════════════
    def _open_settings(self):
        if hasattr(self, "_settings_win") and self._settings_win.winfo_exists():
            self._settings_win.lift()
            return

        keys_backup = dict(self.keys)   # snapshot for cancel

        win = tk.Toplevel(self.root)
        win.title("Opciones — PhasmoClock")
        win.config(bg=C_PANEL)
        win.resizable(False, False)
        win.wm_attributes("-topmost", True)
        win.geometry("480x730")
        self._settings_win = win

        # ── Title ─────────────────────────────────────────────
        tk.Label(win, text="⚙  OPCIONES", font=("Consolas", 13, "bold"),
                 bg=C_PANEL, fg=C_ACCENT).pack(pady=(14, 6))
        tk.Frame(win, bg=C_DIM, height=1).pack(fill="x", padx=16)

        # ── DEFAULTS ──────────────────────────────────────────
        tk.Label(win, text="VALORES POR DEFECTO",
                 font=("Consolas", 8, "bold"), bg=C_PANEL, fg="#66668a"
                 ).pack(anchor="w", padx=16, pady=(10, 2))

        def_frame = tk.Frame(win, bg=C_BLOCK, padx=12, pady=8)
        def_frame.pack(fill="x", padx=16, pady=2)

        map_row = tk.Frame(def_frame, bg=C_BLOCK)
        map_row.pack(fill="x", pady=3)
        tk.Label(map_row, text="Mapa:", font=("Consolas", 9), bg=C_BLOCK,
                 fg="#aaaacc", width=12, anchor="w").pack(side="left")
        map_var = tk.IntVar(value=self.map_idx)
        for i, lbl in enumerate(MAP_LABELS.values()):
            tk.Radiobutton(map_row, text=lbl, variable=map_var, value=i,
                           font=("Consolas", 9), bg=C_BLOCK, fg=C_ACCENT,
                           selectcolor=C_ROOT, activebackground=C_BLOCK,
                           activeforeground=C_GOLD).pack(side="left", padx=6)

        hunt_row = tk.Frame(def_frame, bg=C_BLOCK)
        hunt_row.pack(fill="x", pady=3)
        tk.Label(hunt_row, text="Dificultad:", font=("Consolas", 9), bg=C_BLOCK,
                 fg="#aaaacc", width=12, anchor="w").pack(side="left")
        hunt_var = tk.IntVar(value=self.hunt_idx)
        for i, lbl in enumerate(HUNT_LABELS.values()):
            tk.Radiobutton(hunt_row, text=lbl, variable=hunt_var, value=i,
                           font=("Consolas", 9), bg=C_BLOCK, fg=C_ACCENT,
                           selectcolor=C_ROOT, activebackground=C_BLOCK,
                           activeforeground=C_GOLD).pack(side="left", padx=6)

        # ── DURACIÓN DE CACERÍAS ──────────────────────────────
        tk.Frame(win, bg=C_DIM, height=1).pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(win, text="DURACIÓN DE CACERÍAS (SEGUNDOS)",
                 font=("Consolas", 8, "bold"), bg=C_PANEL, fg="#66668a"
                 ).pack(anchor="w", padx=16, pady=(8, 2))

        times_frame = tk.Frame(win, bg=C_BLOCK, padx=12, pady=8)
        times_frame.pack(fill="x", padx=16, pady=2)

        # Header row for columns
        header_row = tk.Frame(times_frame, bg=C_BLOCK)
        header_row.pack(fill="x", pady=2)
        tk.Label(header_row, text="Dificultad", font=("Consolas", 8, "bold"), bg=C_BLOCK, fg="#66668a", width=12, anchor="w").pack(side="left")
        tk.Label(header_row, text="CHICO", font=("Consolas", 8, "bold"), bg=C_BLOCK, fg="#66668a", width=8, anchor="center").pack(side="left", padx=6)
        tk.Label(header_row, text="MEDIANO", font=("Consolas", 8, "bold"), bg=C_BLOCK, fg="#66668a", width=8, anchor="center").pack(side="left", padx=6)
        tk.Label(header_row, text="GRANDE", font=("Consolas", 8, "bold"), bg=C_BLOCK, fg="#66668a", width=8, anchor="center").pack(side="left", padx=6)

        # 3x3 Grid of entry fields
        entry_vars = {}
        for hk in HUNT_CYCLE:
            row_frame = tk.Frame(times_frame, bg=C_BLOCK)
            row_frame.pack(fill="x", pady=2)
            
            tk.Label(row_frame, text=HUNT_LABELS[hk], font=("Consolas", 9), bg=C_BLOCK, fg="#aaaacc", width=12, anchor="w").pack(side="left")
            
            entry_vars[hk] = {}
            for mk in MAP_CYCLE:
                val = self.hunt_matrix[hk][mk]
                var = tk.StringVar(value=str(int(val) if val.is_integer() else val))
                entry_vars[hk][mk] = var
                
                entry = tk.Entry(row_frame, textvariable=var, font=("Consolas", 9, "bold"), bg=C_ROOT, fg=C_ACCENT,
                                 insertbackground=C_ACCENT, width=8, justify="center", relief="flat")
                entry.pack(side="left", padx=6)

        # Cursed modifier row
        cursed_row = tk.Frame(times_frame, bg=C_BLOCK)
        cursed_row.pack(fill="x", pady=(8, 2))
        tk.Label(cursed_row, text="Mod. Maldita:", font=("Consolas", 9), bg=C_BLOCK, fg="#aaaacc", width=12, anchor="w").pack(side="left")
        cursed_var = tk.StringVar(value=str(int(self.cursed_mod) if self.cursed_mod.is_integer() else self.cursed_mod))
        cursed_entry = tk.Entry(cursed_row, textvariable=cursed_var, font=("Consolas", 9, "bold"), bg=C_ROOT, fg=C_PURPLE,
                                insertbackground=C_PURPLE, width=8, justify="center", relief="flat")
        cursed_entry.pack(side="left", padx=6)
        tk.Label(cursed_row, text="segundos extra", font=("Consolas", 8), bg=C_BLOCK, fg="#66668a").pack(side="left", padx=6)

        # Restablecer valores por defecto
        def reset_defaults():
            for hk in HUNT_CYCLE:
                for mk in MAP_CYCLE:
                    entry_vars[hk][mk].set(str(int(HUNT_MATRIX[hk][mk])))
            cursed_var.set(str(int(CURSED_MOD)))

        reset_row = tk.Frame(times_frame, bg=C_BLOCK)
        reset_row.pack(fill="x", pady=(8, 2))
        tk.Button(reset_row, text="🔄 RESTABLECER TIEMPOS POR DEFECTO",
                  font=("Consolas", 8, "bold"), bg=C_ROOT, fg=C_ACCENT,
                  relief="flat", cursor="hand2", padx=6, pady=4,
                  activebackground=C_BLOCK, activeforeground=C_GOLD,
                  command=reset_defaults).pack(anchor="center")

        # ── CONTROLES ──────────────────────────────────────────
        tk.Frame(win, bg=C_DIM, height=1).pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(win, text="CONTROLES  ·  clic para reasignar  ·  ESC cancela",
                 font=("Consolas", 8, "bold"), bg=C_PANEL, fg="#66668a"
                 ).pack(anchor="w", padx=16, pady=(8, 2))

        ctrl_frame = tk.Frame(win, bg=C_BLOCK, padx=8, pady=6)
        ctrl_frame.pack(fill="x", padx=16, pady=2)

        btn_refs = {}

        def finish_capture(action, new_key):
            """Called on main thread when capture completes or is cancelled."""
            if new_key is None:          # ESC — restore
                btn_refs[action].config(
                    text=self.keys.get(action, "?").upper(),
                    fg=C_ACCENT, bg="#1a1c2e")
            else:
                btn_refs[action].config(text=new_key.upper(),
                                        fg=C_ACCENT, bg="#1a1c2e")

        def start_capture(action):
            # Cancel any previous capture visually
            if self.capturing_action and self.capturing_action in btn_refs:
                btn_refs[self.capturing_action].config(
                    text=self.keys.get(self.capturing_action, "?").upper(),
                    fg=C_ACCENT, bg="#1a1c2e")
            self.capturing_action  = action
            self._capture_callback = finish_capture
            btn_refs[action].config(text="[ PRESIONA ]", fg=C_ORANGE, bg="#2a1500")

        for action, label in ACTION_LABELS.items():
            row = tk.Frame(ctrl_frame, bg=C_BLOCK)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, font=("Consolas", 8), bg=C_BLOCK,
                     fg="#9999bb", anchor="w").pack(side="left", fill="x", expand=True)
            btn = tk.Button(row, text=self.keys[action].upper(),
                            font=("Consolas", 9, "bold"),
                            bg="#1a1c2e", fg=C_ACCENT, relief="flat",
                            activebackground=C_BLOCK, activeforeground=C_GOLD,
                            cursor="hand2", width=12)
            btn.config(command=lambda a=action: start_capture(a))
            btn.pack(side="right", padx=4)
            btn_refs[action] = btn

        # ── Save / Cancel buttons ──────────────────────────────
        tk.Frame(win, bg=C_DIM, height=1).pack(fill="x", padx=16, pady=(10, 0))
        bf = tk.Frame(win, bg=C_PANEL)
        bf.pack(pady=12)

        def save():
            # Validate and update hunt times
            new_matrix = {}
            for hk in HUNT_CYCLE:
                new_matrix[hk] = {}
                for mk in MAP_CYCLE:
                    try:
                        val = float(entry_vars[hk][mk].get())
                        if val < 0:
                            raise ValueError
                        new_matrix[hk][mk] = val
                    except ValueError:
                        new_matrix[hk][mk] = self.hunt_matrix[hk][mk]

            try:
                new_cursed = float(cursed_var.get())
                if new_cursed >= 0:
                    self.cursed_mod = new_cursed
            except ValueError:
                pass

            self.hunt_matrix = new_matrix

            self.capturing_action  = None
            self._capture_callback = None
            new_map  = map_var.get()
            new_hunt = hunt_var.get()
            self.map_idx  = new_map
            self.hunt_idx = new_hunt
            self._recalc()
            self._refresh_hotkey_hint()
            self._save_config()
            win.destroy()

        def cancel():
            self.capturing_action  = None
            self._capture_callback = None
            self.keys = keys_backup
            win.destroy()

        tk.Button(bf, text="  GUARDAR  ", font=("Consolas", 10, "bold"),
                  bg=C_ACCENT, fg=C_ROOT, relief="flat", padx=8, pady=6,
                  activebackground="#00ccaa", cursor="hand2",
                  command=save).pack(side="left", padx=8)
        tk.Button(bf, text="  CANCELAR  ", font=("Consolas", 10, "bold"),
                  bg="#2a2a44", fg="#aaaacc", relief="flat", padx=8, pady=6,
                  activebackground="#3a3a55", cursor="hand2",
                  command=cancel).pack(side="left", padx=8)

        win.protocol("WM_DELETE_WINDOW", cancel)

    def _cfg_row(self, label_text, attr, fg):
        row = tk.Frame(self.cfg_panel, bg=C_PANEL)
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text=label_text, font=F_CONFIG_LBL,
                 bg=C_PANEL, fg="#66668a", width=10, anchor="w").pack(side="left")
        lbl = tk.Label(row, text="---", font=F_CONFIG_VAL, bg=C_PANEL, fg=fg, anchor="w")
        lbl.pack(side="left", padx=4)
        setattr(self, attr, lbl)

    # ══════════════════════════════════════════════════════════
    # BUILD OVERLAY (Toplevel — always transparent, never changes)
    # ══════════════════════════════════════════════════════════
    def _build_overlay(self, wx, wy):
        ov = tk.Toplevel(self.root)
        ov.title(OVERLAY_TITLE)
        ov.withdraw()                                  # hidden until mode 2
        ov.overrideredirect(True)                      # no border — set ONCE, never toggled
        ov.wm_attributes("-topmost", True)
        ov.wm_attributes("-transparentcolor", C_CHROMA)
        ov.config(bg=C_CHROMA)
        ov.geometry(f"{OV_W}x{OV_H}+{wx}+{wy}")
        self.overlay = ov

        # Incense row: icon + countdown (arriba)
        self.ov_inc_row = tk.Frame(ov, bg=C_CHROMA)
        self.ov_inc_row.pack(anchor="w", padx=10, pady=(8,4))

        self.ov_incense_lbl = tk.Label(self.ov_inc_row, text="💨",
                                       font=F_INCENSE_ICO, bg=C_CHROMA, fg=C_DIM)
        self.ov_incense_lbl.pack(side="left")

        self.ov_incense = tk.Label(self.ov_inc_row, text="00:00.0",
                                   font=F_INCENSE_OV, bg=C_CHROMA, fg=C_DIM)
        self.ov_incense.pack(side="left", padx=(8,0))

        # Hunt status + clock (abajo)
        self.ov_status = tk.Label(ov, text="SEGURO",
                                  font=F_STATUS_OV, bg=C_CHROMA, fg=C_ACCENT)
        self.ov_status.pack(anchor="w", padx=10, pady=(4,0))

        self.ov_clock_row = tk.Frame(ov, bg=C_CHROMA)
        self.ov_clock_row.pack(anchor="w", padx=10, pady=(0,8))

        self.ov_cfg_hint = tk.Label(self.ov_clock_row, text="[--]", font=("Consolas", 14, "bold"), bg=C_CHROMA, fg="#44475a")
        self.ov_cfg_hint.pack(side="left", anchor="s", pady=(0,5), padx=(0,4))

        self.ov_clock = tk.Label(self.ov_clock_row, text="00:00.0",
                                 font=F_CLOCK_OV, bg=C_CHROMA, fg="#555577")
        self.ov_clock.pack(side="left")

        # Apply Win32 click-through ONCE after window is ready
        ov.update_idletasks()
        self._set_clickthrough(ov)

    def _set_clickthrough(self, win):
        """Apply WS_EX_LAYERED | WS_EX_TRANSPARENT to a Tk window."""
        try:
            hwnd = ctypes.windll.user32.FindWindowW(None, win.title())
            if not hwnd:
                hwnd = int(win.winfo_id())
            s = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                                s | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        except:
            pass

    # ══════════════════════════════════════════════════════════
    # VIEW MODE CYCLING  (F9)
    # ══════════════════════════════════════════════════════════
    def _cycle_view(self):
        self._beep_thread("view")

        # Llevar posición de una ventana a la otra
        if self.view_mode == 2:
            cx, cy = self.overlay.winfo_x(), self.overlay.winfo_y()
        else:
            cx, cy = self.root.winfo_x(), self.root.winfo_y()

        if self.view_mode == 0:
            # ── Super Minimal: ocultar main, mostrar overlay transparente ──
            self.view_mode = 2
            self.root.withdraw()
            self.overlay.geometry(f"{OV_W}x{OV_H}+{cx}+{cy}")
            self.overlay.deiconify()
            self.overlay.lift()
            self._set_clickthrough(self.overlay)
        else:
            # ── Normal: ventana principal con panel de configuración ──
            self.view_mode = 0
            self.overlay.withdraw()
            if not self.cfg_panel.winfo_ismapped():
                self.cfg_panel.pack(side="left", fill="y",
                                    padx=(10,4), pady=10, ipadx=10, ipady=8)
            self.root.geometry(f"540x400+{cx}+{cy}")
            self.root.deiconify()
            self.root.lift()

    # ══════════════════════════════════════════════════════════
    # CLOSE
    # ══════════════════════════════════════════════════════════
    def _on_close(self):
        self._save_config()
        self.root.destroy()


# ── Entry point ───────────────────────────────────────────────
if __name__ == "__main__":
    try:   ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        try: ctypes.windll.user32.SetProcessDPIAware()
        except: pass

    root = tk.Tk()
    PhasmoClockApp(root)
    root.mainloop()
