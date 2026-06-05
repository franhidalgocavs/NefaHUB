import os, json, time, ctypes, threading, math, struct
import tkinter as tk
import winsound, keyboard

# ── Win32 constants ───────────────────────────────────────────
GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

APPDATA_DIR = os.path.join(os.environ.get("APPDATA", ""), "NefaHUB")
os.makedirs(APPDATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APPDATA_DIR, "config.json")

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
OV_W, OV_H = 420, 280

# ── Ghost rhythm presets (footsteps per second) ───────────────
# Add new ghost types here; interval = 1.0 / rate.
GHOST_RHYTHMS = {
    "default": 1.95,  # 117 BPM → 1.95 fps → beat every ≈ 0.513 s
}

# ── Default key bindings ──────────────────────────────────────
DEFAULT_KEYS = {
    "incense_start":    "1",
    "incense_pause":    "2",
    "hunt":             "3",
    "cycle_map":        "f1",
    "toggle_cursed":    "f2",
    "cycle_difficulty": "f3",
    "cycle_view":       "f9",
    "ghost_rhythm":     "4",
    "bpm_tap":          "5",
}

ACTION_LABELS = {
    "incense_start":    "Iniciar Incienso",
    "incense_pause":    "Pausar Incienso",
    "hunt":             "Cacería / Reset (largo)",
    "cycle_map":        "Ciclar Mapa",
    "toggle_cursed":    "Modo Maldita",
    "cycle_difficulty": "Ciclar Dificultad",
    "cycle_view":       "Cambiar Vista",
    "ghost_rhythm":     "Ritmo Fantasma",
    "bpm_tap":          "Contador BPM",
}

# ==============================================================================
class NefaHUBApp:
# ==============================================================================

    def __init__(self, root, config):
        self.root = root
        self.cfg  = config
        self.root.title(self.cfg.MAIN_TITLE)
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

        # ── Ghost rhythm state ────────────────────────────────
        self.ghost_active   = False
        self.ghost_volume   = 80                              # 0â€“100
        self.ghost_interval = 1.0 / GHOST_RHYTHMS["default"] # ≈ 0.588 s
        self._ghost_thread  = None

        self.bpm_taps = []
        self.bpm_active = False

        self.last_tick_time = time.time()

        # ── View state ────────────────────────────────────────
        self.view_mode = 0
        self.hotkeys_registered = False
        self.capturing_action   = None
        self._capture_callback  = None

        # ── Load saved config ─────────────────────────────────
        wx, wy = self._load_config()

        # ── Build main window ─────────────────────────────────
        self.root.config(bg=self.cfg.C_ROOT)
        self.root.wm_attributes("-topmost", True)
        self.root.geometry(f"540x400+{wx}+{wy}")
        self._build_main_ui()
        self._update_ghost_label()   # initialise ghost indicator

        # ── Build overlay (separate Toplevel, always transparent) ──
        self._build_overlay(wx, wy)

        # ── Init ──────────────────────────────────────────────
        self._setup_hotkeys()
        self._recalc()
        self._tick()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.cfg.beep_thread("welcome")

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # PERSISTENCE
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    def _load_config(self):
        self.hunt_matrix = {hk: {mk: float(HUNT_MATRIX[hk][mk]) for mk in MAP_CYCLE} for hk in HUNT_CYCLE}
        self.cursed_mod = 20.0
        try:
            with open(CONFIG_FILE) as f:
                d = json.load(f)
            self.keys     = {**DEFAULT_KEYS, **d.get("keys", {})}
            self.map_idx  = d.get("default_map_idx",  self.map_idx)
            self.hunt_idx = d.get("default_hunt_idx", self.hunt_idx)
            self.cursed_mod     = d.get("cursed_mod",      self.cursed_mod)
            self.ghost_volume   = d.get("ghost_volume",    self.ghost_volume)
            self.ghost_interval = d.get("ghost_interval",  self.ghost_interval)
            
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
                "ghost_volume":     self.ghost_volume,
                "ghost_interval":   self.ghost_interval,
            }
            # Write flat keys too for C compatibility
            for hk in HUNT_CYCLE:
                for mk in MAP_CYCLE:
                    d[f"time_{hk}_{mk}"] = self.hunt_matrix[hk][mk]
            
            with open(CONFIG_FILE, "w") as f:
                json.dump(d, f, indent=2)
        except:
            pass

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # HOTKEYS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
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
                    elif match_key(ev, self.keys["ghost_rhythm"]):     s(0, self._toggle_ghost_rhythm)
                    elif match_key(ev, self.keys.get("bpm_tap", "5")): s(0, self._on_bpm_tap)
                    elif match_key(ev, "f10"):                         s(0, lambda: os._exit(0))
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
                elif match_key(ev, self.keys.get("bpm_tap", "5")):
                    if is_hold: s(0, self._reset_bpm)

                elif match_key(ev, self.keys["incense_start"]):
                    if is_hold: s(0, self._reset_incense)
                    else:       s(0, self._start_incense)

                elif match_key(ev, self.keys["incense_pause"]):
                    s(0, self._pause_incense)

        keyboard.hook(on_key)
        self.hotkeys_registered = True

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # CONFIG LOGIC
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    def _cycle_map(self):
        if self.cooldown_active:
            return
        old_total = self.hunt_total
        self.map_idx = (self.map_idx + 1) % len(MAP_CYCLE)
        self.cfg.beep_thread("config")
        self._recalc()
        
        if self.hunt_active:
            diff = self.hunt_total - old_total
            self.hunt_time += diff

    def _toggle_cursed(self):
        self.is_cursed = not self.is_cursed
        self.cfg.beep_thread("cursed_on" if self.is_cursed else "cursed_off")
        
        if self.hunt_active:
            if self.is_cursed:
                self.hunt_time += self.cursed_mod
            else:
                self.hunt_time -= self.cursed_mod
            self._recalc()
            color = self.cfg.get_clock_fg(self.hunt_time, "hunt", self.is_cursed)
            status_text = "âš  CACERÃA âš " if self.cfg.IS_PREMIUM else "CACERIA ACTIVA"
            self._set_status(status_text, color)
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
        self.cfg.beep_thread("config")
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
            text=self.cfg.get_cursed_label(self.is_cursed, self.cursed_mod),
            fg=self.cfg.get_cursed_fg(self.is_cursed))
        self.lbl_hunt_val.config(text=HUNT_LABELS[hk])
        self.lbl_total.config(text=f"TOTAL: {int(self.hunt_total)}s")

        cfg_letters = f"[{mk[0].upper()}{hk[0].upper()}]"
        self.lbl_hunt_cfg.config(text=cfg_letters)
        self.ov_cfg_hint.config(text=cfg_letters)

        if not self.hunt_active and not self.cooldown_active:
            self.hunt_time = self.hunt_total
            self._render_clock(self.hunt_time, state="idle", total=self.hunt_total)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # TIMER ACTIONS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
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

    # ─────────────────────────────────────────────────────────
    def _start_hunt(self):
        if self.hunt_active:
            self.hunt_time = 0.0
            self.hunt_active = False
            self.cooldown_active = True
            self.cooldown_time = 0.0
            self.hunt_ref = self.hunt_total
            self._update_ref()
            self.cfg.beep_thread("safe")
            self._set_status("ENFRIAMIENTO", self.cfg.C_BLUE)
            self._render_clock(0.0, state="cooldown")
            return

        self.hunt_active = True
        self.hunt_time   = self.hunt_total
        self.cooldown_active = False
        self.cfg.beep_thread("hunt_start")
        color = self.cfg.get_clock_fg(self.hunt_time, "hunt", self.is_cursed)
        status_text = "âš  CACERÃA âš " if self.cfg.IS_PREMIUM else "CACERIA ACTIVA"
        self._set_status(status_text, color)

    def _reset_hunt(self):
        self.hunt_active = False
        self.cooldown_active = False
        self.hunt_time = self.hunt_total
        self.cfg.beep_thread("safe")
        self._set_status("", self.cfg.C_ACCENT)
        self._render_clock(self.hunt_time, state="idle", total=self.hunt_total)

    def _start_incense(self):
        if self.incense_active:
            # Si estÃ¡ pausado o fue pausado: siempre reiniciar (sin importar el tiempo)
            if self.incense_paused or getattr(self, "incense_was_paused", False):
                self.incense_time   = 0.0
                self.incense_paused = False
                self.incense_was_paused = False
                self.cfg.beep_thread("incense_start")
                col = self.cfg.get_incense_color(self.incense_time)
                self.lbl_incense_status.config(text=self.cfg.LBL_INCENSE_RUN, fg=col)
                self._render_incense("00:00.0", col)
                return
            if self.incense_time < 60.0:
                return          # bloqueado durante el primer minuto (si no estÃ¡ pausado o fue pausado)
            # DespuÃ©s del minuto: REINICIAR (no detener)
            self.incense_time   = 0.0
            self.incense_paused = False
            self.incense_was_paused = False
            self.cfg.beep_thread("incense_start")
            col = self.cfg.get_incense_color(self.incense_time)
            self.lbl_incense_status.config(text=self.cfg.LBL_INCENSE_RUN, fg=col)
            self._render_incense("00:00.0", col)
            return
        self.incense_active = True
        self.incense_paused = False
        self.incense_was_paused = False
        self.incense_time   = 0.0
        self.cfg.beep_thread("incense_start")
        col = self.cfg.get_incense_color(self.incense_time)
        self.lbl_incense_status.config(text=self.cfg.LBL_INCENSE_RUN, fg=col)
        self._render_incense("00:00.0", col)

    def _reset_incense(self):
        self.incense_active = False
        self.incense_paused = False
        self.incense_was_paused = False
        self.incense_time = 0.0
        self.cfg.beep_thread("incense_done")
        self.lbl_incense_status.config(text=self.cfg.LBL_INCENSE_READY, fg=self.cfg.C_ACCENT)
        self._render_incense("00:00.0", self.cfg.C_ACCENT)
        self.ov_incense.config(text="LISTO")

    def _pause_incense(self):
        if not self.incense_active:
            return
        self.incense_paused = not self.incense_paused
        if self.incense_paused:
            self.incense_was_paused = True
        self.cfg.beep_thread("config")
        if self.incense_paused:
            self.lbl_incense_status.config(text=self.cfg.LBL_INCENSE_PAUSE, fg=self.cfg.C_ORANGE)
        else:
            col = self.cfg.get_incense_color(self.incense_time)
            self.lbl_incense_status.config(text=self.cfg.LBL_INCENSE_RUN, fg=col)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # GHOST RHYTHM
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _generate_beep_wav(self, freq=120, duration_ms=30, volume=80, decay=45.0):
        """Build an in-memory WAV buffer with optional exponential-decay envelope.

        freq       : fundamental frequency in Hz (low = thud, high = click)
        duration_ms: total buffer length; decay cuts the tail before it matters
        volume     : 0-100 amplitude scale
        decay      : exponential decay rate â€” 0 = sustained sine,
                     higher values = dryer/shorter percussive hit
                     (e.g. 45 ≈ 30 ms effective duration)
        """
        sample_rate = 44100
        num_samples = int(sample_rate * duration_ms / 1000)
        amplitude   = int(32767 * max(0, min(100, volume)) / 100)
        samples = []
        for i in range(num_samples):
            t   = i / sample_rate
            env = math.exp(-decay * t) if decay > 0 else 1.0
            samples.append(int(amplitude * env * math.sin(2 * math.pi * freq * t)))
        pcm = struct.pack(f'<{num_samples}h', *samples)
        data_size = len(pcm)
        wav  = struct.pack('<4sI4s', b'RIFF', 36 + data_size, b'WAVE')
        wav += struct.pack('<4sIHHIIHH', b'fmt ', 16, 1, 1,
                           sample_rate, sample_rate * 2, 2, 16)
        wav += struct.pack('<4sI', b'data', data_size)
        return wav + pcm

    def _ghost_rhythm_loop(self):
        """Background daemon: plays a dry percussive beat every ghost_interval seconds."""
        next_beat = time.perf_counter()
        while self.ghost_active:
            try:
                # 120 Hz + decay=45 → short dry thud, no tonal sustain
                wav = self._generate_beep_wav(freq=120, duration_ms=30,
                                              volume=self.ghost_volume, decay=45.0)
                winsound.PlaySound(wav, winsound.SND_MEMORY)
            except Exception:
                pass
            
            next_beat += self.ghost_interval
            
            # Sleep precisely until next beat, yielding CPU
            while self.ghost_active:
                now = time.perf_counter()
                if now >= next_beat:
                    break
                time.sleep(max(0.001, min(0.01, next_beat - now)))

    def _toggle_ghost_rhythm(self):
        """Start or stop the ghost rhythm metronome."""
        self.ghost_active = not self.ghost_active
        self.cfg.beep_thread("config")
        if self.ghost_active:
            self._ghost_thread = threading.Thread(
                target=self._ghost_rhythm_loop, daemon=True)
            self._ghost_thread.start()
        self._update_ghost_label()

    def _update_ghost_label(self):
        """Refresh the ghost rhythm indicator in the config panel."""
        k = self.keys.get("ghost_rhythm", "?").upper()
        sym = "●" if self.ghost_active else "○"
        self.lbl_ghost_status.config(
            text=f"👻 [{k}] RITMO {sym}",
            fg=self.cfg.C_ACCENT if self.ghost_active else self.cfg.C_DIM
        )

    def _on_bpm_tap(self):
        now = time.perf_counter()
        if self.bpm_taps and now - self.bpm_taps[-1] > 10.0:
            self.bpm_taps.clear()
            
        self.bpm_taps.append(now)
        if len(self.bpm_taps) > 6:
            self.bpm_taps.pop(0)
            
        self.bpm_active = True
        
        if len(self.bpm_taps) >= 2:
            intervals = [self.bpm_taps[i] - self.bpm_taps[i-1] for i in range(1, len(self.bpm_taps))]
            avg = sum(intervals) / len(intervals)
            bpm = 60.0 / avg if avg > 0 else 0
            
            # Relación Phasmophobia: 117 BPM = 1.7 m/s
            speed = bpm * (1.7 / 117.0)
            
            t = f"BPM: {bpm:.0f} ({speed:.2f} m/s)"
            self.lbl_bpm_status.config(text=t, fg=self.cfg.C_ACCENT)
            if hasattr(self, 'ov_bpm_status'):
                self.ov_bpm_status.config(text=t)
        else:
            self.lbl_bpm_status.config(text="BPM: ---", fg=self.cfg.C_ACCENT)
            if hasattr(self, 'ov_bpm_status'):
                self.ov_bpm_status.config(text="BPM: ---")

    def _reset_bpm(self):
        self.bpm_taps.clear()
        self.bpm_active = False
        self.lbl_bpm_status.config(text="")
        if hasattr(self, 'ov_bpm_status'):
            self.ov_bpm_status.config(text="")
        self.cfg.beep_thread("config")

    # ─────────────────────────────────────────────────────────
    # MAIN TICK LOOP
    # ─────────────────────────────────────────────────────────
    def _tick(self):
        now = time.time()
        dt = now - self.last_tick_time
        self.last_tick_time = now

        if self.bpm_active and self.bpm_taps and (time.perf_counter() - self.bpm_taps[-1] > 10.0):
            self._reset_bpm()

        if self.hunt_active:
            self.hunt_time -= dt
            if self.hunt_time <= 0:
                excess = abs(self.hunt_time)
                self.hunt_time   = 0.0
                self.hunt_active = False
                
                if excess >= 25.0:
                    self.cooldown_active = False
                    self.hunt_time = self.hunt_total
                    self.cfg.beep_thread("safe")
                    self._set_status("", self.cfg.C_ACCENT)
                    self._render_clock(self.hunt_time, state="idle", total=self.hunt_total)
                else:
                    self.cooldown_active = True
                    self.cooldown_time = excess
                    self.hunt_ref    = self.hunt_total
                    self._update_ref()
                    self.cfg.beep_thread("safe")
                    self._set_status("ENFRIAMIENTO", self.cfg.C_BLUE)
                    self._render_clock(self.cooldown_time, state="cooldown")
            else:
                self._render_clock(self.hunt_time, state="hunt")
        elif self.cooldown_active:
            self.cooldown_time += dt
            if self.cooldown_time >= 25.0:
                self.cooldown_active = False
                self.cooldown_time = 25.0
                self._set_status("", self.cfg.C_ACCENT)
                self.hunt_time = self.hunt_total
                self._render_clock(self.hunt_time, state="idle", total=self.hunt_total)
            else:
                self._render_clock(self.cooldown_time, state="cooldown")

        if self.incense_active and not self.incense_paused:
            self.incense_time += dt
            m, s, ms = int(self.incense_time // 60), int(self.incense_time % 60), int((self.incense_time * 10) % 10)
            self._render_incense(f"{m:02d}:{s:02d}.{ms}", self.cfg.get_incense_color(self.incense_time))

        self.root.after(50, self._tick)

    def _render_clock(self, t, state="idle", total=None):
        sign = "-" if t < 0 else ""
        abs_t = abs(t)
        m, s, ms = int(abs_t//60), int(abs_t%60), int((abs_t*10)%10)
        txt = f"{sign}{m:02d}:{s:02d}.{ms}"
        
        fg = self.cfg.get_clock_fg(t, state, self.is_cursed)
        self.lbl_hunt_clock.config(text=txt, fg=fg)
        self.ov_clock.config(text=txt, fg=fg)

        w = self.canvas_bar.winfo_width() or 300
        pct = 0.0
        if state == "hunt":
            pct = max(0, t / self.hunt_total) if self.hunt_total > 0 else 0
        elif state == "cooldown":
            pct = min(1.0, max(0, t / 25.0))
        else: # idle
            if total is None:
                total = self.hunt_total
            pct = min(1.0, max(0, t / total)) if total > 0 else 0

        self.canvas_bar.coords(self.bar_rect, 0, 0, int(w * pct), 8)
        col = self.cfg.get_bar_color(t, state, pct, self.is_cursed)
        self.canvas_bar.itemconfig(self.bar_rect, fill=col)

    def _update_ref(self):
        if getattr(self, "lbl_ref_val", None) is None:
            return
        if self.hunt_ref is None:
            self.lbl_ref_val.config(text="--:--.-", fg=self.cfg.C_DIM)
        else:
            m, s, ms = int(self.hunt_ref//60), int(self.hunt_ref%60), int((self.hunt_ref*10)%10)
            self.lbl_ref_val.config(text=f"{m:02d}:{s:02d}.{ms}", fg=self.cfg.C_GOLD)

    # ─────────────────────────────────────────────────────────
    # BUILD MAIN WINDOW UI
    # ─────────────────────────────────────────────────────────
    def _build_main_ui(self):
        root_f = tk.Frame(self.root, bg=self.cfg.C_ROOT)
        root_f.pack(fill="both", expand=True)

        # LEFT – Config panel
        self.cfg_panel = tk.Frame(root_f, bg=self.cfg.C_PANEL)
        self.cfg_panel.pack(side="left", fill="y", padx=(10,4), pady=10, ipadx=10, ipady=8)

        tk.Label(self.cfg_panel, text=self.cfg.LBL_CONFIG_TITLE,
                 font=self.cfg.F_CONFIG_VAL, bg=self.cfg.C_PANEL, fg=self.cfg.C_ACCENT if self.cfg.IS_PREMIUM else self.cfg.C_DIM).pack(pady=(8,6))

        self._cfg_row(self.cfg.LBL_MAP, "lbl_map_val",   "#ffffff")
        self._cfg_row(self.cfg.LBL_MODE, "lbl_curse_val", self.cfg.C_BLUE)
        self._cfg_row(self.cfg.LBL_DIF,  "lbl_hunt_val",  "#ffffff")

        divider_color = "#222438" if self.cfg.IS_PREMIUM else "#444444"
        tk.Frame(self.cfg_panel, bg=divider_color, height=1).pack(fill="x", padx=8, pady=8)

        total_color = "#66fcf1" if self.cfg.IS_PREMIUM else "#ffffff"
        self.lbl_total = tk.Label(self.cfg_panel, text="TOTAL: --s",
                                  font=self.cfg.F_CONFIG_VAL, bg=self.cfg.C_PANEL, fg=total_color)
        self.lbl_total.pack(pady=2)

        tk.Frame(self.cfg_panel, bg=divider_color, height=1).pack(fill="x", padx=8, pady=8)

        self.lbl_hotkey_hint = tk.Label(self.cfg_panel,
                 text="", font=self.cfg.F_CONFIG_LBL, bg=self.cfg.C_PANEL, fg="#44475a" if self.cfg.IS_PREMIUM else "#aaaaaa", justify="left")
        self.lbl_hotkey_hint.pack(padx=8, pady=4)

        # Ghost rhythm status indicator
        self.lbl_ghost_status = tk.Label(
            self.cfg_panel, text="👻 [F4] RITMO ○",
            font=self.cfg.F_CONFIG_LBL, bg=self.cfg.C_PANEL, fg=self.cfg.C_DIM)
        self.lbl_ghost_status.pack(padx=8, pady=(0, 4))

        bpm_font = ("Consolas", 18, "bold") if self.cfg.IS_PREMIUM else ("Segoe UI", 16, "bold")
        self.lbl_bpm_status = tk.Label(
            self.cfg_panel, text="",
            font=bpm_font, bg=self.cfg.C_PANEL, fg=self.cfg.C_ACCENT)
        self.lbl_bpm_status.pack(padx=8, pady=(0, 4))
        
        self._refresh_hotkey_hint()

        btn_bg = self.cfg.C_ROOT if self.cfg.IS_PREMIUM else "#3e3e3e"
        btn_fg = "#555577" if self.cfg.IS_PREMIUM else "#ffffff"
        btn_relief = "flat" if self.cfg.IS_PREMIUM else "raised"
        tk.Button(self.cfg_panel, text=self.cfg.LBL_SETTINGS_BTN,
                  font=self.cfg.F_CONFIG_LBL, bg=btn_bg, fg=btn_fg,
                  relief=btn_relief, cursor="hand2", bd=0 if self.cfg.IS_PREMIUM else 1,
                  activebackground=self.cfg.C_BLOCK if self.cfg.IS_PREMIUM else "#4e4e4e", 
                  activeforeground=self.cfg.C_ACCENT if self.cfg.IS_PREMIUM else "#ffffff",
                  command=self._open_settings).pack(pady=(2, 8))

        # RIGHT – HUD panel
        self.hud_panel = tk.Frame(root_f, bg=self.cfg.C_ROOT)
        self.hud_panel.pack(side="right", fill="both", expand=True, padx=(4,10), pady=10)

        # Incense block (arriba)
        ib = tk.Frame(self.hud_panel, bg=self.cfg.C_BLOCK)
        ib.pack(fill="x", pady=(0,6))

        inc_row = tk.Frame(ib, bg=self.cfg.C_BLOCK)
        inc_row.pack(fill="x", padx=10, pady=(8,8))

        self.lbl_incense_status = tk.Label(inc_row, text=self.cfg.LBL_INCENSE_LBL,
                                           font=self.cfg.F_CONFIG_VAL, bg=self.cfg.C_BLOCK, fg=self.cfg.C_DIM)
        self.lbl_incense_status.pack(side="left")

        self.lbl_incense_clock = tk.Label(inc_row, text="00:00.0",
                                          font=self.cfg.F_INCENSE, bg=self.cfg.C_BLOCK, fg=self.cfg.C_DIM)
        self.lbl_incense_clock.pack(side="right")

        # Hunt block (abajo)
        hb = tk.Frame(self.hud_panel, bg=self.cfg.C_BLOCK)
        hb.pack(fill="x")

        top_row = tk.Frame(hb, bg=self.cfg.C_BLOCK)
        top_row.pack(fill="x", padx=10, pady=(8,0))

        self.lbl_status = tk.Label(top_row, text="",
                                   font=self.cfg.F_STATUS_MAIN, bg=self.cfg.C_BLOCK, fg=self.cfg.C_ACCENT if self.cfg.IS_PREMIUM else self.cfg.C_GREEN)
        self.lbl_status.pack(side="left")

        if self.cfg.IS_PREMIUM:
            ref_f = tk.Frame(top_row, bg=self.cfg.C_BLOCK)
            ref_f.pack(side="right")
            tk.Label(ref_f, text=self.cfg.LBL_LAST_LBL, font=self.cfg.F_REF_LBL, bg=self.cfg.C_BLOCK, fg="#333355").pack(anchor="e")
            self.lbl_ref_val = tk.Label(ref_f, text="--:--.-",
                                        font=self.cfg.F_REF_VAL, bg=self.cfg.C_BLOCK, fg=self.cfg.C_DIM)
            self.lbl_ref_val.pack(anchor="e")
        else:
            self.lbl_ref_val = None

        # Clock + bar wrapper
        self.hunt_clock_frame = tk.Frame(hb, bg=self.cfg.C_BLOCK)
        self.hunt_clock_frame.pack(fill="x")

        # Inner frame to keep the clock centered
        clk_inner = tk.Frame(self.hunt_clock_frame, bg=self.cfg.C_BLOCK)
        clk_inner.pack(pady=(0,4))

        cfg_letters_font = ("Consolas", 18, "bold") if self.cfg.IS_PREMIUM else ("Segoe UI", 12, "bold")
        cfg_letters_fg = "#44475a" if self.cfg.IS_PREMIUM else self.cfg.C_DIM
        self.lbl_hunt_cfg = tk.Label(clk_inner, text="[--]", font=cfg_letters_font, bg=self.cfg.C_BLOCK, fg=cfg_letters_fg)
        self.lbl_hunt_cfg.pack(side="left", padx=(0, 6), anchor="s", pady=(0,8))

        clock_init_fg = "#555577" if self.cfg.IS_PREMIUM else self.cfg.C_DIM
        self.lbl_hunt_clock = tk.Label(clk_inner, text="00:00.0",
                                       font=self.cfg.F_CLOCK_MAIN, bg=self.cfg.C_BLOCK, fg=clock_init_fg)
        self.lbl_hunt_clock.pack(side="left")

        self.canvas_bar = tk.Canvas(self.hunt_clock_frame, height=8, bg=self.cfg.C_ROOT, highlightthickness=0)
        self.canvas_bar.pack(fill="x", padx=10, pady=(0,8))
        self.bar_rect = self.canvas_bar.create_rectangle(0, 0, 0, 8, fill="#2a2a3a" if self.cfg.IS_PREMIUM else "#d0d0d0", width=0)


    def _refresh_hotkey_hint(self):
        """Update the key-hint label in the config panel from current bindings."""
        k = self.keys
        lines = [
            f"[{k['incense_start'].upper()}]  Incienso",
            f"[{k['incense_pause'].upper()}]  Pausa",
            f"[{k['hunt'].upper()}]  Cacería",
            f"[{k['cycle_view'].upper()}] Vista" if self.cfg.IS_PREMIUM else f"[{k['cycle_view'].upper()}]  Vista",
            f"[{k.get('bpm_tap', '5').upper()}]  Contador BPM",
        ]
        self.lbl_hotkey_hint.config(text="\n".join(lines))
        self._update_ghost_label()

    # ─────────────────────────────────────────────────────────
    def _open_settings(self):
        if hasattr(self, "_settings_win") and self._settings_win.winfo_exists():
            self._settings_win.lift()
            return

        keys_backup = dict(self.keys)

        win = tk.Toplevel(self.root)
        win.title(self.cfg.LBL_SETTINGS_WIN)
        win.config(bg=self.cfg.C_PANEL)
        win.resizable(False, True)
        win.wm_attributes("-topmost", True)
        win.geometry("480x680")
        self._settings_win = win

        divider_color = self.cfg.C_DIM if self.cfg.IS_PREMIUM else "#444444"
        defaults_fg   = "#66668a" if self.cfg.IS_PREMIUM else self.cfg.C_DIM
        lbl_font      = ("Consolas", 9) if self.cfg.IS_PREMIUM else ("Segoe UI", 9)
        lbl_fg        = "#aaaacc" if self.cfg.IS_PREMIUM else "#ffffff"
        entry_font     = ("Consolas", 9, "bold") if self.cfg.IS_PREMIUM else ("Segoe UI", 9, "bold")
        entry_lbl_font = ("Consolas", 9)         if self.cfg.IS_PREMIUM else ("Segoe UI", 9)
        hdr_font       = ("Consolas", 8, "bold") if self.cfg.IS_PREMIUM else ("Segoe UI", 8, "bold")
        entry_fg       = self.cfg.C_ACCENT if self.cfg.IS_PREMIUM else "#ffffff"
        entry_bg       = self.cfg.C_ROOT
        entry_relief   = "flat" if self.cfg.IS_PREMIUM else "sunken"

        # ── Save/Cancel pinned at the bottom (pack FIRST so they stay visible) ──
        bottom_sep = tk.Frame(win, bg=divider_color, height=1)
        bottom_sep.pack(side="bottom", fill="x")
        bf = tk.Frame(win, bg=self.cfg.C_PANEL)
        bf.pack(side="bottom", pady=8)

        # ── Scrollable content area ────────────────────────────────────────────
        scroll_canvas = tk.Canvas(win, bg=self.cfg.C_PANEL, highlightthickness=0)
        vscroll = tk.Scrollbar(win, orient="vertical", command=scroll_canvas.yview)
        inner = tk.Frame(scroll_canvas, bg=self.cfg.C_PANEL)

        inner.bind("<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.create_window((0, 0), window=inner, anchor="nw", width=460)
        scroll_canvas.configure(yscrollcommand=vscroll.set)

        def _on_scroll(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        win.bind("<MouseWheel>", _on_scroll)

        vscroll.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        # ── Title ─────────────────────────────────────────────────────────────
        title_font = ("Consolas", 13, "bold") if self.cfg.IS_PREMIUM else ("Segoe UI", 12, "bold")
        title_fg   = self.cfg.C_ACCENT if self.cfg.IS_PREMIUM else "#ffffff"
        tk.Label(inner, text=self.cfg.LBL_SETTINGS_BTN, font=title_font,
                 bg=self.cfg.C_PANEL, fg=title_fg).pack(pady=(14, 6))
        tk.Frame(inner, bg=divider_color, height=1).pack(fill="x", padx=16)

        # ── DEFAULTS ──────────────────────────────────────────────────────────
        tk.Label(inner, text=self.cfg.LBL_DEFAULTS,
                 font=self.cfg.F_CONFIG_LBL, bg=self.cfg.C_PANEL, fg=defaults_fg
                 ).pack(anchor="w", padx=16, pady=(10, 2))

        def_frame = tk.Frame(inner, bg=self.cfg.C_BLOCK, padx=12, pady=8)
        def_frame.pack(fill="x", padx=16, pady=2)

        map_row = tk.Frame(def_frame, bg=self.cfg.C_BLOCK)
        map_row.pack(fill="x", pady=3)
        tk.Label(map_row, text="Mapa:", font=lbl_font, bg=self.cfg.C_BLOCK,
                 fg=lbl_fg, width=12, anchor="w").pack(side="left")

        map_var      = tk.IntVar(value=self.map_idx)
        radio_fg     = self.cfg.C_ACCENT if self.cfg.IS_PREMIUM else "#ffffff"
        radio_active = self.cfg.C_GOLD   if self.cfg.IS_PREMIUM else "#ffffff"
        for i, lbl in enumerate(MAP_LABELS.values()):
            tk.Radiobutton(map_row, text=lbl, variable=map_var, value=i,
                           font=lbl_font, bg=self.cfg.C_BLOCK, fg=radio_fg,
                           selectcolor=self.cfg.C_ROOT, activebackground=self.cfg.C_BLOCK,
                           activeforeground=radio_active).pack(side="left", padx=6)

        hunt_row = tk.Frame(def_frame, bg=self.cfg.C_BLOCK)
        hunt_row.pack(fill="x", pady=3)
        tk.Label(hunt_row, text="Dificultad:", font=lbl_font, bg=self.cfg.C_BLOCK,
                 fg=lbl_fg, width=12, anchor="w").pack(side="left")
        hunt_var = tk.IntVar(value=self.hunt_idx)
        for i, lbl in enumerate(HUNT_LABELS.values()):
            tk.Radiobutton(hunt_row, text=lbl, variable=hunt_var, value=i,
                           font=lbl_font, bg=self.cfg.C_BLOCK, fg=radio_fg,
                           selectcolor=self.cfg.C_ROOT, activebackground=self.cfg.C_BLOCK,
                           activeforeground=radio_active).pack(side="left", padx=6)

        # ── DURACIÃ“N DE CACERÃAS ──────────────────────────────────────────────
        tk.Frame(inner, bg=divider_color, height=1).pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(inner, text=self.cfg.LBL_HUNT_DURATION,
                 font=self.cfg.F_CONFIG_LBL, bg=self.cfg.C_PANEL, fg=defaults_fg
                 ).pack(anchor="w", padx=16, pady=(8, 2))

        times_frame = tk.Frame(inner, bg=self.cfg.C_BLOCK, padx=12, pady=8)
        times_frame.pack(fill="x", padx=16, pady=2)

        header_row = tk.Frame(times_frame, bg=self.cfg.C_BLOCK)
        header_row.pack(fill="x", pady=2)
        tk.Label(header_row, text="Dificultad", font=hdr_font, bg=self.cfg.C_BLOCK,
                 fg=defaults_fg, width=12, anchor="w").pack(side="left")
        for col in ("CHICO", "MEDIANO", "GRANDE"):
            tk.Label(header_row, text=col, font=hdr_font, bg=self.cfg.C_BLOCK,
                     fg=defaults_fg, width=8, anchor="center").pack(side="left", padx=6)

        entry_vars = {}
        for hk in HUNT_CYCLE:
            row_frame = tk.Frame(times_frame, bg=self.cfg.C_BLOCK)
            row_frame.pack(fill="x", pady=2)
            tk.Label(row_frame, text=HUNT_LABELS[hk], font=entry_lbl_font,
                     bg=self.cfg.C_BLOCK, fg=lbl_fg, width=12, anchor="w").pack(side="left")
            entry_vars[hk] = {}
            for mk in MAP_CYCLE:
                val = self.hunt_matrix[hk][mk]
                var = tk.StringVar(value=str(int(val) if float(val).is_integer() else val))
                entry_vars[hk][mk] = var
                tk.Entry(row_frame, textvariable=var, font=entry_font,
                         bg=entry_bg, fg=entry_fg, insertbackground=entry_fg,
                         width=8, justify="center", relief=entry_relief,
                         bd=0 if self.cfg.IS_PREMIUM else 1).pack(side="left", padx=6)

        cursed_row = tk.Frame(times_frame, bg=self.cfg.C_BLOCK)
        cursed_row.pack(fill="x", pady=(8, 2))
        tk.Label(cursed_row, text="Mod. Maldita:", font=entry_lbl_font,
                 bg=self.cfg.C_BLOCK, fg=lbl_fg, width=12, anchor="w").pack(side="left")
        cursed_var = tk.StringVar(
            value=str(int(self.cursed_mod) if float(self.cursed_mod).is_integer() else self.cursed_mod))
        cursed_fg = self.cfg.C_PURPLE if self.cfg.IS_PREMIUM else "#ffffff"
        tk.Entry(cursed_row, textvariable=cursed_var, font=entry_font,
                 bg=entry_bg, fg=cursed_fg, insertbackground=cursed_fg,
                 width=8, justify="center", relief=entry_relief,
                 bd=0 if self.cfg.IS_PREMIUM else 1).pack(side="left", padx=6)
        tk.Label(cursed_row, text="segundos extra", font=hdr_font,
                 bg=self.cfg.C_BLOCK, fg=defaults_fg).pack(side="left", padx=6)

        def reset_defaults():
            for hk in HUNT_CYCLE:
                for mk in MAP_CYCLE:
                    entry_vars[hk][mk].set(str(int(HUNT_MATRIX[hk][mk])))
            cursed_var.set(str(int(CURSED_MOD)))

        reset_row = tk.Frame(times_frame, bg=self.cfg.C_BLOCK)
        reset_row.pack(fill="x", pady=(8, 2))
        reset_bg     = self.cfg.C_ROOT if self.cfg.IS_PREMIUM else "#3e3e3e"
        reset_fg     = self.cfg.C_ACCENT if self.cfg.IS_PREMIUM else "#ffffff"
        reset_relief = "flat" if self.cfg.IS_PREMIUM else "raised"
        tk.Button(reset_row, text=self.cfg.LBL_RESET_BTN,
                  font=entry_font, bg=reset_bg, fg=reset_fg,
                  relief=reset_relief, cursor="hand2", padx=6, pady=4,
                  activebackground=self.cfg.C_BLOCK if self.cfg.IS_PREMIUM else "#4e4e4e",
                  activeforeground=self.cfg.C_GOLD  if self.cfg.IS_PREMIUM else "#ffffff",
                  command=reset_defaults, bd=0 if self.cfg.IS_PREMIUM else 1).pack(anchor="center")

        # ── CONTROLES (key bindings) ──────────────────────────────────────────
        tk.Frame(inner, bg=divider_color, height=1).pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(inner, text=self.cfg.LBL_CONTROLES,
                 font=self.cfg.F_CONFIG_LBL, bg=self.cfg.C_PANEL, fg=defaults_fg
                 ).pack(anchor="w", padx=16, pady=(8, 2))

        ctrl_frame = tk.Frame(inner, bg=self.cfg.C_BLOCK, padx=8, pady=6)
        ctrl_frame.pack(fill="x", padx=16, pady=2)

        btn_refs = {}

        def finish_capture(action, new_key):
            if new_key is None:
                btn_refs[action].config(
                    text=self.keys.get(action, "?").upper(),
                    fg="#ffffff", bg="#3e3e3e")
            else:
                btn_refs[action].config(text=new_key.upper(),
                                        fg="#ffffff", bg="#3e3e3e")

        def start_capture(action):
            if self.capturing_action and self.capturing_action in btn_refs:
                btn_refs[self.capturing_action].config(
                    text=self.keys.get(self.capturing_action, "?").upper(),
                    fg="#ffffff", bg="#3e3e3e")
            self.capturing_action  = action
            self._capture_callback = finish_capture
            btn_refs[action].config(text="[ PRESIONA ]", fg="#000000", bg="#ffc107")

        ctrl_lbl_font = ("Consolas", 8) if self.cfg.IS_PREMIUM else ("Segoe UI", 8)
        for action, label in ACTION_LABELS.items():
            row = tk.Frame(ctrl_frame, bg=self.cfg.C_BLOCK)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, font=ctrl_lbl_font, bg=self.cfg.C_BLOCK,
                     fg="#aaaaaa", anchor="w").pack(side="left", fill="x", expand=True)
            btn = tk.Button(row, text=self.keys[action].upper(), font=entry_font,
                            bg="#3e3e3e", fg="#ffffff", relief="raised", bd=1,
                            activebackground="#4e4e4e", activeforeground="#ffffff",
                            cursor="hand2", width=12)
            btn.config(command=lambda a=action: start_capture(a))
            btn.pack(side="right", padx=4)
            btn_refs[action] = btn

        # ── RITMO FANTASMA ────────────────────────────────────────────────────
        tk.Frame(inner, bg=divider_color, height=1).pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(inner, text="RITMO FANTASMA",
                 font=self.cfg.F_CONFIG_LBL, bg=self.cfg.C_PANEL, fg=defaults_fg
                 ).pack(anchor="w", padx=16, pady=(8, 2))

        ghost_frame = tk.Frame(inner, bg=self.cfg.C_BLOCK, padx=12, pady=8)
        ghost_frame.pack(fill="x", padx=16, pady=(2, 14))

        info_row = tk.Frame(ghost_frame, bg=self.cfg.C_BLOCK)
        info_row.pack(fill="x", pady=(0, 4))
        
        bpm_val = 60.0 / self.ghost_interval if self.ghost_interval > 0 else 0
        tk.Label(info_row, text="BPM Manual:", font=lbl_font, bg=self.cfg.C_BLOCK,
                 fg=lbl_fg, width=12, anchor="w").pack(side="left")
        
        bpm_var = tk.StringVar(value=str(round(bpm_val)))
        tk.Entry(info_row, textvariable=bpm_var, font=entry_font, width=8,
                 bg=self.cfg.C_ROOT, fg="#ffffff", insertbackground="#ffffff",
                 relief="flat", highlightbackground=self.cfg.C_DIM,
                 highlightcolor=self.cfg.C_ACCENT, highlightthickness=1).pack(side="left")

        vol_row = tk.Frame(ghost_frame, bg=self.cfg.C_BLOCK)
        vol_row.pack(fill="x", pady=2)
        tk.Label(vol_row, text="Volumen:", font=lbl_font, bg=self.cfg.C_BLOCK,
                 fg=lbl_fg, width=12, anchor="w").pack(side="left")
        volume_var = tk.IntVar(value=self.ghost_volume)
        slider_fg  = self.cfg.C_ACCENT if self.cfg.IS_PREMIUM else "#ffffff"
        tk.Scale(vol_row, from_=0, to=100, orient=tk.HORIZONTAL,
                 variable=volume_var, length=200,
                 bg=self.cfg.C_BLOCK, fg=slider_fg, troughcolor=self.cfg.C_ROOT,
                 highlightthickness=0, showvalue=True,
                 font=lbl_font).pack(side="left", padx=6)

        # ── Closures + bottom buttons ─────────────────────────────────────────
        def save():
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
            try:
                new_bpm = float(bpm_var.get())
                if new_bpm > 0:
                    self.ghost_interval = 60.0 / new_bpm
            except ValueError:
                pass
            self.hunt_matrix  = new_matrix
            self.ghost_volume = volume_var.get()
            self.capturing_action  = None
            self._capture_callback = None
            self.map_idx  = map_var.get()
            self.hunt_idx = hunt_var.get()
            self._recalc()
            self._refresh_hotkey_hint()
            self._save_config()
            win.destroy()

        def cancel():
            self.capturing_action  = None
            self._capture_callback = None
            self.keys = keys_backup
            win.destroy()

        save_btn_font = ("Consolas", 9, "bold") if self.cfg.IS_PREMIUM else ("Segoe UI", 9, "bold")
        tk.Button(bf, text="  GUARDAR  ", font=save_btn_font,
                  bg="#3e3e3e", fg="#ffffff", relief="raised", bd=1, padx=8, pady=4,
                  activebackground="#4e4e4e", cursor="hand2",
                  command=save).pack(side="left", padx=8)
        tk.Button(bf, text="  CANCELAR  ", font=save_btn_font,
                  bg="#3e3e3e", fg="#ffffff", relief="raised", bd=1, padx=8, pady=4,
                  activebackground="#4e4e4e", cursor="hand2",
                  command=cancel).pack(side="left", padx=8)

        win.protocol("WM_DELETE_WINDOW", cancel)
    def _cfg_row(self, label_text, attr, fg):
        row = tk.Frame(self.cfg_panel, bg=self.cfg.C_PANEL)
        row.pack(fill="x", padx=8, pady=2)
        
        cfg_lbl_font = ("Consolas", 9) if self.cfg.IS_PREMIUM else ("Segoe UI", 9)
        cfg_val_font = ("Consolas", 9, "bold") if self.cfg.IS_PREMIUM else ("Segoe UI", 9, "bold")
        
        tk.Label(row, text=label_text, font=cfg_lbl_font,
                 bg=self.cfg.C_PANEL, fg="#aaaaaa", width=12 if self.cfg.IS_PREMIUM else 10, anchor="w").pack(side="left")
        lbl = tk.Label(row, text="---", font=cfg_val_font, bg=self.cfg.C_PANEL, fg=fg, anchor="w")
        lbl.pack(side="left", padx=4)
        setattr(self, attr, lbl)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # BUILD OVERLAY
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    def _build_overlay(self, wx, wy):
        ov = tk.Toplevel(self.root)
        ov.title(self.cfg.OVERLAY_TITLE)
        ov.withdraw()                                  # hidden until mode 2
        ov.overrideredirect(True)                      # no border
        ov.wm_attributes("-topmost", True)
        ov.wm_attributes("-transparentcolor", self.cfg.C_CHROMA)
        ov.config(bg=self.cfg.C_CHROMA)
        ov.geometry(f"{OV_W}x{OV_H}+{wx}+{wy}")
        self.overlay = ov

        # Incense row: icon + countdown (arriba)
        self.ov_inc_row = tk.Frame(ov, bg=self.cfg.C_CHROMA)
        self.ov_inc_row.pack(anchor="w", padx=10, pady=(8,4))

        self.ov_incense_lbl = tk.Label(self.ov_inc_row, text="💨",
                                       font=self.cfg.F_INCENSE_ICO, bg=self.cfg.C_CHROMA, fg=self.cfg.C_DIM)
        self.ov_incense_lbl.pack(side="left")

        self.ov_incense = tk.Label(self.ov_inc_row, text="00:00.0",
                                   font=self.cfg.F_INCENSE_OV, bg=self.cfg.C_CHROMA, fg=self.cfg.C_DIM)
        self.ov_incense.pack(side="left", padx=(8,0))

        # Hunt status + clock (abajo)
        self.ov_status = tk.Label(ov, text="",
                                   font=self.cfg.F_STATUS_OV, bg=self.cfg.C_CHROMA, fg=self.cfg.C_GREEN)
        self.ov_status.pack(anchor="w", padx=10, pady=(4,0))

        self.ov_clock_row = tk.Frame(ov, bg=self.cfg.C_CHROMA)
        self.ov_clock_row.pack(anchor="w", padx=10, pady=(0,8))

        cfg_letters_font = ("Consolas", 18, "bold") if self.cfg.IS_PREMIUM else ("Segoe UI", 12, "bold")
        self.ov_cfg_hint = tk.Label(self.ov_clock_row, text="[--]", font=cfg_letters_font, bg=self.cfg.C_CHROMA, fg=self.cfg.C_DIM)
        self.ov_cfg_hint.pack(side="left", anchor="s", pady=(0,5), padx=(0,4))

        self.ov_clock = tk.Label(self.ov_clock_row, text="00:00.0",
                                 font=self.cfg.F_CLOCK_OV, bg=self.cfg.C_CHROMA, fg=self.cfg.C_DIM)
        self.ov_clock.pack(side="left")

        ov_bpm_font = ("Consolas", 16, "bold") if self.cfg.IS_PREMIUM else ("Segoe UI", 14, "bold")
        self.ov_bpm_status = tk.Label(ov, text="",
                                      font=ov_bpm_font, bg=self.cfg.C_CHROMA, fg=self.cfg.C_ACCENT)
        self.ov_bpm_status.pack(anchor="w", padx=10, pady=(4,0))

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

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # VIEW MODE CYCLING (F9)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    def _cycle_view(self):
        self.cfg.beep_thread("view")
        
        # Llevar posiciÃ³n de una ventana a la otra
        if self.view_mode == 2:
            cx, cy = self.overlay.winfo_x(), self.overlay.winfo_y()
        else:
            cx, cy = self.root.winfo_x(), self.root.winfo_y()

        if self.view_mode == 0:
            # Pasar a Modo 2: Overlay transparente flotante
            self.view_mode = 2
            self.root.withdraw()
            self.overlay.geometry(f"{OV_W}x{OV_H}+{cx}+{cy}")
            self.overlay.deiconify()
            self.overlay.lift()
            self._set_clickthrough(self.overlay)
        else:
            # Volver a Modo 0: Normal
            self.view_mode = 0
            self.overlay.withdraw()
            if not self.cfg_panel.winfo_ismapped():
                self.cfg_panel.pack(side="left", fill="y", padx=(10,4), pady=10, ipadx=10, ipady=8)
            self.root.geometry(f"540x400+{cx}+{cy}")
            self.root.deiconify()
            self.root.lift()

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # CLOSE
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    def _on_close(self):
        self._save_config()
        self.root.destroy()
