# ⏱️ NefaHUB - Suite de Temporizadores para Investigación Paranormal

¡Bienvenido a **NefaHUB**! Esta es una suite profesional de herramientas de asistencia en tiempo real diseñada para ayudarte a rastrear con precisión absoluta la duración de las cacerías e intervalos de incienso en tus juegos de investigación paranormal favoritos (como *Phasmophobia*).

Para adaptarnos a tu estilo, ofrecemos dos variantes comerciales:
1. **NefaHUB Base (Código Abierto):** Una versión limpia, sobria y directa en Python con interfaz de ventana clásica y soporte de overlay transparente. Ideal para la comunidad de GitHub.
2. **NefaHUB Premium (Versión Completa):** La experiencia definitiva en juego, que incluye el HUD flotante cyberpunk translúcido neón e intangible, la versión nativa compilada en C, lógica de avisos visuales avanzados por color y personalización completa de teclas y configuraciones.

---

## 📊 Comparativa de Versiones

| Característica | NefaHUB Base (GitHub Free) | NefaHUB Premium (Premium Paga) |
| :--- | :---: | :---: |
| **Formato de Entrega** | Archivo script Python `.py` | **Ejecutable `.exe` compilado en C nativo** |
| **Consumo de CPU/RAM** | Medio (requiere intérprete de Python) | **Casi nulo (0.01% CPU / 2MB RAM)** |
| **Estilo Visual** | Tema oscuro sobrio (Segoe UI) | **HUD Cyberpunk Translúcido Neón** |
| **Intangibilidad (Click-Through)** | **Sí (puedes jugar y disparar a través del HUD)** | **Sí (puedes jugar y disparar a través del HUD)** |
| **Reloj de Incienso con Alertas** | Monocromático estándar | **Dinámico (cambia a rojo en etapas críticas)** |
| **Configuraciones Personalizadas** | Guardado en `%APPDATA%/NefaHUB` | **Personalización milimétrica con guardado JSON** |
| **Señales Auditivas** | Bips estándar del sistema | **Efectos Sci-Fi y arpegios de piano clásicos** |
| **Columna de Historial (ÚLTIMO)** | No incluida | **Incluida (referencia rápida del último tiempo)** |

---

## 🚀 Requisitos e Instalación

### Versión Base (`nefahub_base.py`)
Requiere **Python 3.10+** y la biblioteca `keyboard` instalada en tu sistema.
1. Abre tu consola (PowerShell/CMD) **como Administrador** (necesario para la captura de teclas global).
2. Instala la dependencia necesaria:
   ```bash
   pip install keyboard
   ```
3. Ejecuta la aplicación:
   ```bash
   python nefahub_base.py
   ```

### Versión Premium (`nefahub_premium.exe` / `nefahub_premium.py`)
* **Ejecutable compilado (.exe):** No requiere Python. Simplemente ejecuta el archivo `nefahub_premium.exe` **como Administrador** y configura el juego en **Ventana sin bordes (Borderless Windowed)** para disfrutar del overlay transparente flotante en tiempo real.
* **Script Python (.py):** Si prefieres ejecutar el código fuente de la versión Premium, corre:
  ```bash
  python nefahub_premium.py
  ```

---

## ⌨️ Controles Rápidos y Atajos de Teclado

### Controles Fijos en NefaHUB Base (Personalizables en Opciones)
* **`1`** (Teclado estándar o Numpad): Inicia o reinicia el reloj de Incienso.
* **`2`**: Pausa o reanuda el reloj de Incienso.
* **`3`**: Inicia la cacería de forma instantánea. **Mantener presionado** durante 0.4s reinicia y limpia el temporizador.
* **`F1`**: Cambia el tamaño del mapa actual (Chico $\rightarrow$ Mediano $\rightarrow$ Grande).
* **`F2`**: Alterna entre cacería Normal y Cacería Maldita (agrega automáticamente +20 segundos).
* **`F3`**: Cambia la dificultad/duración de cacería base (Baja $\rightarrow$ Media $\rightarrow$ Alta).
* **`F9`**: Alterna Vista (Modo Configuración $\leftrightarrow$ Modo Overlay transparente).

### Controles por Defecto en NefaHUB Premium (Personalizables)
* **`1`**: Iniciar/Reiniciar Incienso.
* **`2`**: Pausar/Reanudar Incienso.
* **`3`**: Iniciar Cacería (Mantener presionado para resetear).
* **`F1`**: Ciclar Mapa.
* **`F2`**: Alternar cacería Maldita.
* **`F3`**: Ciclar Dificultad.
* **`F9`**: **Alternar Vista (Modo Configuración $\leftrightarrow$ Modo HUD transparente)**.
* *(Nota: Puedes reasignar cualquiera de estas teclas en tiempo real desde el botón `⚙ OPCIONES` de cualquiera de las versiones)*

---

## 🛠️ Compilación desde el Código Fuente (Premium)

Si realizas modificaciones al código fuente en C de la versión Premium (`nefahub_premium.c`), puedes recompilar el ejecutable nativo usando el script automatizado:
1. Abre una consola en el directorio del proyecto como Administrador.
2. Ejecuta:
   ```bash
   build.bat
   ```
   *(Requiere tener configurado el compilador GCC de MinGW en tu Path, el cual se autodetectará de tu instalación clásica de MSYS2)*
