# ⏱️ NefaHUB - Suite de Temporizadores para Investigación Paranormal

¡Bienvenido a **NefaHUB**! Esta es una herramienta de asistencia en tiempo real de código abierto (Open Source), diseñada para ayudarte a rastrear con precisión absoluta la duración de las cacerías e intervalos de incienso en tus juegos de investigación paranormal favoritos (como *Phasmophobia*).

NefaHUB te brinda la experiencia definitiva en juego, incluyendo un HUD flotante translúcido e intangible, lógica de avisos visuales avanzados por color y personalización completa de teclas y configuraciones en una aplicación de extremadamente bajo consumo y rendimiento nativo.

---

## 🚀 Requisitos e Instalación

### Opción 1: Ejecutable Compilado (.exe) - RECOMENDADO
No requiere instalar nada extra ni descargar dependencias.
1. Descargá `nefahub.exe` desde la sección **[Releases](../../releases)** (no de ningún otro sitio) y ejecutalo **como Administrador** (es necesario para poder capturar los atajos de teclado globales mientras juegas).
   > [!WARNING]
   > Al no contar con un certificado de firma de código digital (que es de pago), es muy probable que Windows Defender (SmartScreen) te muestre una pantalla azul indicando que la aplicación es desconocida. Haz clic en **"Más información"** y luego en **"Ejecutar de todas formas"**.

#### 🔒 Transparencia de la compilación
Cada release de `nefahub.exe` se genera automáticamente con **GitHub Actions** directamente desde el código fuente público (`nefahub.c`) de este repositorio — no se sube ningún binario compilado a mano. Podés:
- Ver el log de compilación completo en la pestaña **[Actions](../../actions)** de cada release.
- Verificar la integridad del archivo descargado contra el `nefahub.exe.sha256` publicado junto a cada release.
- Compilarlo vos mismo con `build.bat` y comparar el resultado.


### Opción 2: Ejecutar desde el código fuente Python (`.py`)
Si prefieres correr o explorar el código fuente original en Python:
1. Asegúrate de tener **Python 3.10+** instalado en tu PC.
2. Abre tu consola **como Administrador**.
3. Instala la dependencia necesaria para el teclado:
   ```bash
   pip install keyboard
   ```
4. Ejecuta la aplicación:
   ```bash
   python NefaHUB/nefahub_core.py
   ```

---

## 📖 Tutorial Básico de Uso (Primeros Pasos)

¡Usar NefaHUB es muy intuitivo! El flujo de trabajo ideal en una partida de Phasmophobia es el siguiente:

1. **Configuración Inicial:** 
   Antes de entrar a la casa, usa **`F1`** para seleccionar el tamaño del mapa y **`F3`** para la dificultad. El reloj calculará automáticamente los segundos exactos que durará la cacería.
2. **Posicionamiento del Overlay:**
   En NefaHUB (antes de jugar), arrastra la ventana principal a la esquina de la pantalla donde te resulte más cómoda. Luego presiona **`F9`** para pasar al **Modo Overlay**. La ventana se volverá transparente, ignorará tus clics (para que puedas jugar sin problemas) y se quedará flotando por encima del juego.
3. **Durante una Cacería:**
   Apenas escuches que la puerta principal se cierra o el fantasma empieza a cazar, presiona **`3`**. El cronómetro comenzará a bajar y la barra indicadora cambiará de color. Cuando el reloj llegue a cero, pasará automáticamente al **Modo Enfriamiento** (25 segundos), que es tu tiempo de gracia asegurado en el que el fantasma no puede volver a cazar.
   * *Tip pro:* Si durante el enfriamiento te das cuenta de que el mapa o la dificultad no eran los correctos, ¡podés cambiarlos con `F1` o `F3` y NefaHUB reajustará el reloj de enfriamiento retroactivamente!
4. **Modo Maldito (F2):**
   Si alguien rompe un espejo maldito, usa la ouija u otro objeto maldito, la cacería durará 20 segundos más. Presiona **`F2`** para activar el modo maldito en NefaHUB y sincronizar los relojes al instante.
5. **Uso de Inciensos (Smudge Sticks):**
   Cuando le tires incienso al fantasma para cegarlo, presiona **`1`**. NefaHUB iniciará un cronómetro de 90 segundos. Su color te indicará visualmente si es seguro caminar por la casa o si el fantasma ya puede volver a atacar. (Mantén presionado **`1`** si necesitas reiniciar este cronómetro).
6. **Contador de BPM / Ritmo:**
   ¿Querés identificar al fantasma por la velocidad de sus pasos? Presiona repetidamente **`5`** al ritmo de los pasos del fantasma. NefaHUB calculará instantáneamente sus BPM y te mostrará su velocidad estimada en *metros por segundo (m/s)*.
7. **Cierre Seguro:**
   Presiona **`F10`** en cualquier momento para salir limpiamente y guardar tu configuración.

---

## ⌨️ Controles y Atajos de Teclado (Globales)

*Puedes reasignar cualquiera de estas teclas en tiempo real presionando el botón `⚙ OPCIONES` dentro de NefaHUB.*

* **`1`**: Iniciar cronómetro de Incienso. (Mantener presionado 0.4s para Resetear).
* **`2`**: Pausar/Reanudar Incienso.
* **`3`**: Iniciar cronómetro de Cacería. (Mantener presionado 0.4s para Resetear).
* **`4`**: Activar/Desactivar metrónomo interno (ritmo fantasma).
* **`5`**: Contador de BPM (Presionar repetidamente al ritmo de los pasos. Mantener para resetear).
* **`F1`**: Ciclar tamaño del Mapa (Chico $\rightarrow$ Mediano $\rightarrow$ Grande).
* **`F2`**: Activar/Desactivar modo Cacería Maldita (+20s).
* **`F3`**: Ciclar Dificultad base (Baja $\rightarrow$ Media $\rightarrow$ Alta).
* **`F9`**: Alternar vista (**Modo Configuración** $\leftrightarrow$ **Modo HUD Overlay Transparente**).
* **`F10`**: Cerrar NefaHUB.

---

## 🛠️ Compilación desde el Código Fuente (Versión C Nativa)

Si realizas modificaciones al código fuente en C (`nefahub.c`), puedes recompilar el ejecutable nativo en Windows usando el script incluido:
1. Abre una consola en el directorio del proyecto.
2. Ejecuta el script:
   ```bash
   build.bat
   ```
   *(Requiere tener configurado el compilador GCC de MinGW-w64 en tu `PATH`, por ejemplo desde MSYS2).*

---

## 📄 Licencia

Este proyecto es software libre bajo los términos de la **[GNU General Public License v3.0](LICENSE)**. Podés usarlo, modificarlo y redistribuirlo libremente, siempre que cualquier versión derivada se mantenga también bajo GPLv3 y de código abierto.
