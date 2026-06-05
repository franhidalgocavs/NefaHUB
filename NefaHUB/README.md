# ⏱️ NefaHUB Base - Asistente de Investigación Paranormal (Código Abierto)

¡Bienvenido a **NefaHUB Base**! Esta es una herramienta profesional de asistencia en tiempo real de código abierto diseñada para ayudarte a rastrear con precisión la duración de las cacerías e intervalos de incienso en tus juegos de investigación paranormal favoritos (como *Phasmophobia*).

Esta versión es limpia, ligera y cuenta con una interfaz oscura y un cómodo overlay transparente e intangible de juego.

---

## 🚀 Requisitos e Instalación

NefaHUB Base requiere **Python 3.10+** y la biblioteca `keyboard` instalada en tu sistema.

1. Abre tu consola (PowerShell/CMD) **como Administrador** (es obligatorio para la captura de teclas global en segundo plano).
2. Instala la dependencia necesaria:
   ```bash
   pip install keyboard
   ```
3. Descarga `nefahub_base.py` y ejecútalo en la consola:
   ```bash
   python nefahub_base.py
   ```

---

## ⌨️ Controles Rápidos y Atajos de Teclado (Personalizables)

* **`1`** (Teclado estándar o Numpad): Inicia o reinicia el reloj de Incienso.
* **`2`**: Pausa o reanuda el reloj de Incienso.
* **`3`**: Inicia la cacería de forma instantánea. **Mantener presionado** durante 0.4s limpia y reinicia el temporizador.
* **`F1`**: Cambia el tamaño del mapa actual (Chico $\rightarrow$ Mediano $\rightarrow$ Grande).
* **`F2`**: Alterna entre cacería Normal y Cacería Maldita (agrega automáticamente +20 segundos).
* **`F3`**: Cambia la dificultad/duración de cacería base (Baja $\rightarrow$ Media $\rightarrow$ Alta).
* **`F9`**: **Alternar Vista (Modo Ajustes $\leftrightarrow$ Modo HUD Transparente)**.

> [!TIP]
> Puedes reasignar cualquiera de estas teclas y personalizar las duraciones de las cacerías en tiempo real haciendo clic en el botón **Opciones** de la ventana de configuración.

---

## ⚙️ Características Clave

* **Tema Oscuro Profesional:** Estética sobria estilo editor de código (Segoe UI).
* **Overlay Transparente de Juego (F9):** Oculta la ventana y proyecta un HUD translúcido e intangible (`click-through`) sobre el juego para que juegues y apuntes sin bloqueos.
* **Almacenamiento Centralizado:** Las configuraciones se guardan de forma segura en `%APPDATA%/NefaHUB/config.json`, manteniendo limpia la carpeta de ejecución.
* **Consistencia Teórica:** Remoción del cartel "SEGURO" por precisión UX en Phasmophobia (el fantasma puede cazar por cordura).

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. ¡Siéntete libre de clonarlo, mejorarlo y compartirlo con la comunidad!
