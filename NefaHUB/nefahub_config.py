import time, threading, winsound

# ==============================================================================
class BaseConfig:
# ==============================================================================
    IS_PREMIUM = False
    
    # ── Titles ────────────────────────────────────────────────────────
    MAIN_TITLE    = "NefaHUB Base"
    OVERLAY_TITLE = "NefaHUBBaseOV"
    
    # ── Colors ────────────────────────────────────────────────────────
    C_ROOT   = "#1e1e1e"   # Gris muy oscuro tradicional (estilo editor)
    C_PANEL  = "#2d2d2d"   # Gris de panel estándar
    C_BLOCK  = "#252526"   # Gris para bloques del HUD
    C_ACCENT = "#3b82f6"   # Azul estándar activo apagado
    C_DIM    = "#888888"   # Gris secundario apagado
    C_RED    = "#ef4444"   # Rojo estándar apagado
    C_ORANGE = "#f97316"   # Naranja estándar
    C_GOLD   = "#eab308"   # Amarillo/Dorado sobrio
    C_PURPLE = "#a855f7"   # Morado estándar apagado
    C_BLUE   = "#3b82f6"   # Azul estándar
    C_GREEN  = "#22c55e"   # Verde estándar
    C_CHROMA = "#010101"   # Color transparente clave del overlay
    
    # ── Fonts ─────────────────────────────────────────────────────────
    F_CLOCK_MAIN  = ("Segoe UI", 36, "bold")
    F_CLOCK_OV    = ("Segoe UI", 30, "bold")
    F_STATUS_MAIN = ("Segoe UI", 14, "bold")
    F_STATUS_OV   = ("Segoe UI", 9, "bold")
    F_INCENSE     = ("Segoe UI", 16, "bold")
    F_INCENSE_OV  = ("Segoe UI", 30, "bold")
    F_INCENSE_ICO = ("Segoe UI", 24)
    F_CONFIG_LBL  = ("Segoe UI", 9)
    F_CONFIG_VAL  = ("Segoe UI", 9, "bold")
    F_REF_LBL     = ("Segoe UI", 8)
    F_REF_VAL     = ("Segoe UI", 10, "bold")

    # ── Text & UI Strings ─────────────────────────────────────────────
    LBL_CONFIG_TITLE  = "Ajustes"
    LBL_MAP           = "Mapa:"
    LBL_MODE          = "Modo:"
    LBL_DIF           = "Dif:"
    LBL_SETTINGS_BTN  = "Opciones"
    LBL_SETTINGS_WIN  = "Opciones — NefaHUB Base"
    LBL_INCENSE_LBL   = "Incienso"
    LBL_INCENSE_READY = "Incienso listo"
    LBL_INCENSE_RUN   = "Incienso corriendo"
    LBL_INCENSE_PAUSE = "Pausado"
    LBL_LAST_LBL      = "ÚLTIMO"
    
    LBL_DEFAULTS      = "Valores por defecto"
    LBL_HUNT_DURATION = "Duración de cacerías (segundos)"
    LBL_CONTROLES     = "Controles  ·  clic para reasignar  ·  ESC cancela"
    LBL_RESET_BTN     = "Restablecer tiempos por defecto"

    # ── Custom behaviors & logic ──────────────────────────────────────
    def get_cursed_label(self, is_cursed, cursed_mod):
        return f"Maldita (+{int(cursed_mod)}s)" if is_cursed else "Normal"
        
    def get_cursed_fg(self, is_cursed):
        return self.C_RED if is_cursed else self.C_DIM

    def get_incense_color(self, incense_time):
        """Monocromo para versión Base (siempre cian neón)."""
        return self.C_ACCENT

    def get_clock_fg(self, t, state, is_cursed):
        if state == "idle":
            return self.C_PURPLE if is_cursed else self.C_DIM
        elif state == "hunt":
            return self.C_PURPLE if is_cursed else self.C_RED
        elif state == "cooldown":
            if t < 0 and is_cursed:
                return self.C_PURPLE
            elif t >= 20.0:
                return self.C_RED
            else:
                return self.C_BLUE
        return self.C_DIM

    def get_bar_color(self, t, state, pct, is_cursed):
        if state == "hunt":
            return self.C_PURPLE if is_cursed else self.C_RED
        elif state == "cooldown":
            return self.C_RED if t >= 20.0 else self.C_BLUE
        else: # idle
            return "#d0d0d0"

    # ── Beeps / Sounds ────────────────────────────────────────────────
    def _beep(self, f, ms):
        try: winsound.Beep(f, ms)
        except: pass

    def beep_thread(self, action):
        def run():
            if action in ["hunt_start", "cursed_on"]:
                self._beep(880, 200)
            elif action in ["welcome", "safe", "incense_start", "incense_done"]:
                self._beep(600, 150)
            else:
                self._beep(750, 80)
        threading.Thread(target=run, daemon=True).start()


# ==============================================================================
class PremiumConfig(BaseConfig):
# ==============================================================================
    IS_PREMIUM = True
    
    # ── Titles ────────────────────────────────────────────────────────
    MAIN_TITLE    = "NefaHUB Premium"
    OVERLAY_TITLE = "NefaHUBPremiumOV"
    
    # ── Colors ────────────────────────────────────────────────────────
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
    C_CHROMA = "#010101"
    
    # ── Fonts ─────────────────────────────────────────────────────────
    F_CLOCK_MAIN  = ("Consolas", 46, "bold")
    F_CLOCK_OV    = ("Consolas", 42, "bold")
    F_STATUS_MAIN = ("Impact",   18)
    F_STATUS_OV   = ("Consolas", 10, "bold")
    F_INCENSE     = ("Consolas", 20, "bold")
    F_INCENSE_OV  = ("Consolas", 42, "bold")
    F_INCENSE_ICO = ("Consolas", 34)
    F_CONFIG_LBL  = ("Consolas",  8, "bold")
    F_CONFIG_VAL  = ("Consolas",  9, "bold")
    F_REF_LBL     = ("Consolas",  7, "bold")
    F_REF_VAL     = ("Consolas", 12, "bold")

    # ── Text & UI Strings ─────────────────────────────────────────────
    LBL_CONFIG_TITLE  = "CONFIGURACIÓN"
    LBL_MAP           = "F1  MAPA:"
    LBL_MODE          = "F2  MODO:"
    LBL_DIF           = "F3  DIF:"
    LBL_SETTINGS_BTN  = "⚙ OPCIONES"
    LBL_SETTINGS_WIN  = "Opciones — NefaHUB Premium"
    LBL_INCENSE_LBL   = "INCIENSO [1]"
    LBL_INCENSE_READY = "INCIENSO LISTO"
    LBL_INCENSE_RUN   = "🔥 INCIENSO"
    LBL_INCENSE_PAUSE = "⏸ PAUSADO"
    LBL_LAST_LBL      = "ÚLTIMO"
    
    LBL_DEFAULTS      = "VALORES POR DEFECTO"
    LBL_HUNT_DURATION = "DURACIÓN DE CACERÍAS (SEGUNDOS)"
    LBL_CONTROLES     = "CONTROLES  ·  clic para reasignar  ·  ESC cancela"
    LBL_RESET_BTN     = "🔄 RESTABLECER TIEMPOS POR DEFECTO"

    # ── Custom behaviors & logic ──────────────────────────────────────
    def get_cursed_label(self, is_cursed, cursed_mod):
        return f"MALDITA 💀  +{int(cursed_mod)}s" if is_cursed else "NORMAL      +0s"
        
    def get_cursed_fg(self, is_cursed):
        return self.C_PURPLE if is_cursed else self.C_BLUE

    def get_incense_color(self, incense_time):
        """Rojo 0-5s, 20-25s y 60-90s."""
        t = incense_time
        if t < 5.0 or (20.0 <= t < 25.0) or (60.0 <= t < 90.0):
            return self.C_RED
        return self.C_ACCENT

    def get_clock_fg(self, t, state, is_cursed):
        if state == "idle":
            return self.C_PURPLE if is_cursed else self.C_DIM
        elif state == "hunt":
            if is_cursed:
                return self.C_PURPLE
            else:
                return self.C_RED if int(time.time()*3) % 2 == 0 else self.C_ORANGE
        elif state == "cooldown":
            if t < 0 and is_cursed:
                return self.C_PURPLE
            elif t >= 20.0:
                return self.C_RED
            else:
                return self.C_BLUE
        return self.C_DIM

    def get_bar_color(self, t, state, pct, is_cursed):
        if state == "hunt":
            if is_cursed:
                return self.C_PURPLE
            else:
                return self.C_RED if pct > 0.6 else self.C_ORANGE if pct > 0.3 else self.C_ACCENT
        elif state == "cooldown":
            return self.C_RED if t >= 20.0 else self.C_BLUE
        else: # idle
            return "#2a2a3a"

    # ── Beeps / Sounds ────────────────────────────────────────────────
    def beep_thread(self, action):
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
