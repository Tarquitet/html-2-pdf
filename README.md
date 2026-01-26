# 📄 HTML to PDF Generator (Ultimate Edition)

> **Un generador profesional que convierte archivos HTML locales a PDFs optimizados, resolviendo problemas de _lazy-loading_ y reduciendo el peso final drásticamente.**

**HTML to PDF Generator** es una herramienta de escritorio (GUI) en Python diseñada para desarrolladores y diseñadores. Utiliza el motor de **Playwright** (Chromium) para asegurar que el diseño (CSS/JS) se renderice perfectamente y aplica un post-procesado con **PyMuPDF** para optimizar el peso de las imágenes sin sacrificar calidad visual.

![1769443738317](images/README/1769443738317.png)

## ✨ Características Principales (v5)

- **🌐 Servidor Local Integrado:** Para evitar bloqueos de seguridad del navegador (CORS) con archivos locales, el script monta un servidor HTTP temporal que sirve tus recursos y tipografías correctamente.
- **📜 Solución a Lazy-Loading (Auto-Scroll):** Inyecta un script que hace scroll automático hasta el final de la página, forzando la carga de todas las imágenes _lazy-loaded_ antes de capturar el PDF.
- **🧠 Motor de Compresión Híbrido:** Analiza cada imagen del PDF final:
  - Si la imagen tiene transparencia (Alpha), la conserva como **PNG** optimizado.
  - Si es opaca, la convierte a **JPEG** con la calidad definida en el panel de control.
- **🛡️ Limpieza de Metadatos:** Elimina los datos EXIF de las imágenes y los metadatos del PDF (Autor, Fecha de creación, Software) para mayor privacidad y un archivo más limpio.
- **🏷️ Nombrado Inteligente Multi-idioma:** Detecta sufijos como `-en` o `_en` en el archivo HTML original para etiquetar automáticamente el PDF generado (ej. `CV_David_Pinto_ENG.pdf`).

---

## ⚙️ Requisitos e Instalación

El script cuenta con un **Auto-Instalador Robusto**. Al ejecutarlo por primera vez, descargará las librerías de Python e instalará el navegador Chromium necesario para Playwright.

**Requisitos del sistema:**

- Python 3.8 o superior.

**Dependencias (instaladas automáticamente):**

- `playwright` (Renderizado web)
- `pymupdf / fitz` (Edición y compresión de PDF)
- `pillow` (Procesamiento de imágenes)

### Ejecución

```bash
python 5_HTML-2-PDF-Python.py

(Nota: La primera ejecución puede tardar un par de minutos mientras Playwright descarga Chromium en segundo plano).
📖 Guía de Uso

    Seleccionar Archivos: Haz clic en ➕ Agregar HTMLs y selecciona uno o varios archivos .html de tu proyecto.

    Configurar Calidad: Usa el deslizador para ajustar la calidad JPEG de las imágenes (Recomendado: 75% para buen balance entre peso y nitidez).

    Privacidad: Marca la casilla "Eliminar Metadatos" si vas a distribuir el PDF públicamente.

    Generar: Elige tu carpeta de salida y presiona 🚀 GENERAR PDFS.

📈 Evolución del Proyecto (Changelog)

    v0: Implementación inicial (Playwright + Servidor Local). Renderizado básico con auto-scroll para lazy-loading.

    v1: Agregado el control de Escala Optimizada para redimensionar imágenes gigantes según el nivel de calidad seleccionado.

    v2: Implementación del Modo Privacidad (No-Metadata) para limpiar rastros de creación en el PDF.

    v3 - v4: Desarrollo del Motor Híbrido PNG/JPEG. Versiones anteriores perdían optimización o arruinaban las transparencias; la v4 logra el balance perfecto.

    v5 (Actual): Integración de Renombrado Inteligente según el idioma del archivo (-en). Eliminación de páginas finales en blanco que Playwright suele generar por error.

⚠️ Limitaciones y Notas Técnicas

    Consumo de Memoria: El procesamiento por lotes de archivos muy largos requiere una cantidad moderada de RAM, ya que PyMuPDF abre los documentos completos en memoria para optimizarlos.

    Entornos CI/CD (Servidores): Si usas esto en un entorno sin interfaz gráfica (Headless Linux), asegúrate de que Playwright tenga instaladas las dependencias del sistema operativo (playwright install-deps).
```
