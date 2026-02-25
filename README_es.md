# 📄 Generador HTML a PDF (Edición Definitiva)

> **Una herramienta profesional que convierte archivos HTML locales a PDFs optimizados, resolviendo problemas de lazy-loading y reduciendo drásticamente el peso final.**

HTML to PDF Generator es una aplicación de escritorio en Python que utiliza Playwright (Chromium) para asegurar el render correcto de CSS/JS y aplica un post-procesado con PyMuPDF para optimizar las imágenes sin perder calidad.

![1769443738317](images/README/1769443738317.png)

## ✨ Características Principales (v5)

- **Servidor Local Integrado:** Evita bloqueos CORS del navegador con archivos locales sirviendo recursos y tipografías correctamente.
- **Auto-Scroll para Lazy-Loading:** Inyecta un script que desplaza la página hasta el final para forzar la carga de imágenes lazy-loaded antes de capturar.
- **Motor de Compresión Híbrido:** Conserva PNG para imágenes con transparencia y convierte a JPEG las opacas según la calidad seleccionada.
- **Limpieza de Metadatos:** Elimina EXIF y metadatos del PDF (Autor, Fecha, Software) para privacidad y menor peso.
- **Renombrado Inteligente Multi-idioma:** Detecta sufijos `-en` o `_en` para nombrar PDFs (ej. `CV_David_Pinto_ENG.pdf`).

---

## ⚙️ Requisitos e Instalación

El script incluye un auto-instalador que descarga dependencias e instala Chromium para Playwright en la primera ejecución.

**Requisitos:**

- Python 3.8 o superior.

**Dependencias (instaladas automáticamente):**

- `playwright`
- `pymupdf` / `fitz`
- `pillow`

Ejecución:

```bash
python 5_HTML-2-PDF-Python.py
```

Nota: la primera ejecución puede tardar mientras Playwright descarga Chromium.

[![Read in English](https://img.shields.io/badge/Read%20in%20English-EN-blue?style=flat-square&logo=github)](README.md)
