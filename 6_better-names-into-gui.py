import sys
import os
import subprocess
import threading
import io
import socket
import http.server
import socketserver
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import re

# --- AUTO-INSTALADOR ---
def setup():
    libs = ['playwright', 'pymupdf', 'pillow']
    for lib in libs:
        try:
            if lib == 'pymupdf': import fitz
            else: __import__(lib)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try: p.chromium.launch()
            except: subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    except: pass

setup()

from playwright.sync_api import sync_playwright
import fitz 
from PIL import Image

class ProPDFGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Tarquitet PDF - Professional Naming V6")
        self.root.geometry("750x850")
        
        self.html_files = []
        self.port = 0
        self.server_process = None
        
        # --- DATOS POR DEFECTO ---
        self.first_name = tk.StringVar(value="David")
        self.last_name = tk.StringVar(value="Pinto")
        self.role_es = tk.StringVar(value="Ingeniero Multimedia")
        self.role_en = tk.StringVar(value="Multimedia Engineer")
        
        # Patrones de nombre
        # {Type}: CV / Portfolio
        # {Name}: DavidPinto / David_Pinto
        # {Role}: Ingeniero...
        # {Lang}: ES / EN
        self.naming_pattern = tk.StringVar(value="{Type}_{Name}_{Role}_{Lang}")
        
        # Variables de Imagen (Heredadas de la V4)
        self.quality_var = tk.IntVar(value=80)
        self.max_width_var = tk.IntVar(value=1600)
        self.clean_meta_var = tk.BooleanVar(value=True)
        
        self.base_dir = os.path.join(os.getcwd(), "assets", "pdf")
        if not os.path.exists(self.base_dir):
            try: os.makedirs(self.base_dir)
            except: self.base_dir = os.getcwd()
        self.out_dir = self.base_dir
        
        self.build_ui()

    def build_ui(self):
        style = ttk.Style()
        style.configure("Bold.TLabel", font=("Arial", 10, "bold"))
        
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill="both", expand=True)

        # HEADER
        ttk.Label(main_frame, text="GENERADOR DE PDFS PROFESIONALES", font=("Arial", 14, "bold")).pack(pady=5)
        ttk.Label(main_frame, text="Optimizado para ATS y RRHH", foreground="gray").pack(pady=(0, 15))

        # --- SECCIÓN 1: DATOS DEL CANDIDATO ---
        info_frame = ttk.LabelFrame(main_frame, text="1. Identidad Profesional", padding=10)
        info_frame.pack(fill="x", pady=5)
        
        grid = ttk.Frame(info_frame)
        grid.pack(fill="x")
        
        ttk.Label(grid, text="Nombre:").grid(row=0, column=0, padx=5, sticky="w")
        ttk.Entry(grid, textvariable=self.first_name, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(grid, text="Apellido:").grid(row=0, column=2, padx=5, sticky="w")
        ttk.Entry(grid, textvariable=self.last_name, width=15).grid(row=0, column=3, padx=5)
        
        ttk.Label(grid, text="Rol (ES):").grid(row=1, column=0, padx=5, sticky="w", pady=5)
        ttk.Entry(grid, textvariable=self.role_es, width=25).grid(row=1, column=1, columnspan=3, sticky="we", padx=5)

        ttk.Label(grid, text="Rol (EN):").grid(row=2, column=0, padx=5, sticky="w")
        ttk.Entry(grid, textvariable=self.role_en, width=25).grid(row=2, column=1, columnspan=3, sticky="we", padx=5)

        # --- SECCIÓN 2: ESTRATEGIA DE NOMBRADO ---
        name_frame = ttk.LabelFrame(main_frame, text="2. Estructura del Nombre del Archivo", padding=10)
        name_frame.pack(fill="x", pady=10)
        
        ttk.Label(name_frame, text="Patrón de Variables:", style="Bold.TLabel").pack(anchor="w")
        
        pat_combo = ttk.Combobox(name_frame, textvariable=self.naming_pattern, width=50)
        pat_combo['values'] = [
            "{Type}_{Name}_{Role}",           # Estándar Global
            "{Name}_{Type}_{Role}",           # Centrado en la persona
            "CV_{Name}_{Role}_{Lang}",        # Específico para CV
            "{Type}_{Role}_{Name}",           # Centrado en el cargo
            "{Last}_{First}_{Type}_{Role}"    # Formal Académico
        ]
        pat_combo.pack(fill="x", pady=5)
        
        ttk.Label(name_frame, text="Variables disponibles: {Name}, {First}, {Last}, {Type}, {Role}, {Lang}", 
                  font=("Consolas", 8), foreground="#555").pack(anchor="w")
        
        # PREVIEW LABEL
        self.preview_lbl = ttk.Label(name_frame, text="Ejemplo: CV_David_Pinto_Ingeniero_Multimedia.pdf", 
                                     foreground="blue", font=("Arial", 9, "italic"))
        self.preview_lbl.pack(pady=5)
        
        # Actualizar preview cuando cambian las variables
        self.naming_pattern.trace("w", self.update_preview)
        self.first_name.trace("w", self.update_preview)
        self.last_name.trace("w", self.update_preview)

        # --- SECCIÓN 3: ARCHIVOS Y CALIDAD ---
        ctrl_frame = ttk.LabelFrame(main_frame, text="3. Configuración Técnica (Heredado V4)", padding=10)
        ctrl_frame.pack(fill="x", pady=5)
        
        btn_f = ttk.Frame(ctrl_frame)
        btn_f.pack(fill="x")
        ttk.Button(btn_f, text="Seleccionar HTMLs", command=self.sel_files).pack(side="left", fill="x", expand=True, padx=(0,5))
        ttk.Button(btn_f, text="Carpeta Salida", command=self.sel_dir).pack(side="left", padx=(5,0))
        
        self.lbl_files = ttk.Label(ctrl_frame, text="0 archivos", font=("Arial", 8))
        self.lbl_files.pack(pady=2)

        # Sliders en Grid
        sld_f = ttk.Frame(ctrl_frame)
        sld_f.pack(fill="x", pady=5)
        
        ttk.Label(sld_f, text="Calidad IMG:").pack(side="left")
        ttk.Scale(sld_f, from_=10, to=100, variable=self.quality_var).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Label(sld_f, textvariable=self.quality_var).pack(side="left")
        
        ttk.Separator(ctrl_frame, orient="horizontal").pack(fill="x", pady=5)
        ttk.Checkbutton(ctrl_frame, text="Limpiar Metadatos (Privacidad)", variable=self.clean_meta_var).pack(anchor="w")

        # BOTÓN FINAL
        self.btn_go = ttk.Button(main_frame, text="GENERAR PDFS PROFESIONALES", command=self.start, state="disabled")
        self.btn_go.pack(fill="x", pady=20, ipady=10)
        
        self.progress = ttk.Progressbar(main_frame, mode="determinate")
        self.progress.pack(fill="x")
        self.status = ttk.Label(main_frame, text="Listo")
        self.status.pack()

    def update_preview(self, *args):
        # Simulación de un archivo CV en español
        try:
            example = self.build_filename(
                "cv-index.html", 
                self.first_name.get(), 
                self.last_name.get(),
                self.role_es.get(),
                self.role_en.get(),
                self.naming_pattern.get()
            )
            self.preview_lbl.config(text=f"Ejemplo de salida: {example}")
        except: pass

    # --- LÓGICA DE NOMBRADO INTELIGENTE ---
    def clean_str(self, s):
        # Elimina caracteres ilegales y reemplaza espacios por _
        s = s.strip()
        # Normalizar tildes podría ir aquí si se requiere
        return re.sub(r'[^a-zA-Z0-9_-]', '_', s)

    def build_filename(self, original_filename, first, last, role_es, role_en, pattern):
        lower_name = original_filename.lower()
        
        # 1. DETECTAR IDIOMA
        is_english = '-en' in lower_name or '_en' in lower_name
        lang_code = "EN" if is_english else "ES"
        
        # 2. DETECTAR TIPO
        doc_type = "Portfolio" # Default
        if "cv" in lower_name or "hoja" in lower_name or "resume" in lower_name:
            doc_type = "Resume" if is_english else "CV"
        elif "dossier" in lower_name:
            doc_type = "Dossier"
        
        # 3. SELECCIONAR ROL SEGÚN IDIOMA
        role_txt = role_en if is_english else role_es
        
        # 4. PREPARAR VARIABLES LIMPIAS
        # Usamos CamelCase o SnakeCase para profesionalismo
        full_name = f"{first}{last}" # CamelCase pegado
        first_clean = self.clean_str(first)
        last_clean = self.clean_str(last)
        role_clean = self.clean_str(role_txt)
        
        # 5. REEMPLAZAR EN PATRÓN
        final_name = pattern.replace("{Type}", doc_type)
        final_name = final_name.replace("{Name}", full_name)
        final_name = final_name.replace("{First}", first_clean)
        final_name = final_name.replace("{Last}", last_clean)
        final_name = final_name.replace("{Role}", role_clean)
        final_name = final_name.replace("{Lang}", lang_code)
        
        # Limpieza final de guiones dobles por si alguna variable estaba vacía
        final_name = final_name.replace("__", "_").replace("-_", "_").strip("_")
        
        return f"{final_name}.pdf"

    def sel_files(self):
        files = filedialog.askopenfilenames(filetypes=[("HTML", "*.html")])
        if files:
            self.html_files = files
            self.lbl_files.config(text=f"{len(files)} seleccionados")
            self.btn_go.config(state="normal")
            self.update_preview()

    def sel_dir(self):
        d = filedialog.askdirectory(initialdir=self.base_dir)
        if d: self.out_dir = d

    def start(self):
        threading.Thread(target=self.process_batch, daemon=True).start()

    # --- SERVIDOR Y GENERACIÓN (Engine V4) ---
    def start_server(self, root_dir):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        self.port = sock.getsockname()[1]
        sock.close()
        handler = http.server.SimpleHTTPRequestHandler
        self.httpd = socketserver.TCPServer(("localhost", self.port), handler)
        os.chdir(root_dir)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop_server(self):
        if hasattr(self, 'httpd'):
            self.httpd.shutdown()
            self.httpd.server_close()

    def process_batch(self):
        self.btn_go.config(state="disabled")
        self.progress["maximum"] = len(self.html_files)
        
        # Datos capturados de la UI (Thread safe capture)
        first = self.first_name.get()
        last = self.last_name.get()
        r_es = self.role_es.get()
        r_en = self.role_en.get()
        pat = self.naming_pattern.get()
        
        q = self.quality_var.get()
        mw = self.max_width_var.get()
        clean = self.clean_meta_var.get()

        project_root = os.path.dirname(self.html_files[0])
        self.start_server(project_root)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                
                for idx, html_path in enumerate(self.html_files):
                    fname = os.path.basename(html_path)
                    
                    # Generar nombre profesional
                    final_name = self.build_filename(fname, first, last, r_es, r_en, pat)
                    
                    self.status.config(text=f"Procesando: {final_name}...")
                    
                    page = browser.new_page()
                    page.goto(f"http://localhost:{self.port}/{fname}", wait_until="networkidle")
                    
                    # Auto-scroll para lazy loading
                    page.evaluate("""async () => {
                        await new Promise((resolve) => {
                            let totalHeight = 0;
                            const distance = 200;
                            const timer = setInterval(() => {
                                const scrollHeight = document.body.scrollHeight;
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if(totalHeight >= scrollHeight){
                                    clearInterval(timer);
                                    window.scrollTo(0, 0);
                                    resolve();
                                }
                            }, 40);
                        });
                    }""")
                    page.wait_for_timeout(2000) # Espera de seguridad
                    
                    pdf_bytes = page.pdf(format="A4", print_background=True, margin={"top":"0","bottom":"0","left":"0","right":"0"})
                    page.close()
                    
                    self.compress_and_save(pdf_bytes, final_name, q, mw, clean)
                    self.progress["value"] = idx + 1
                
                browser.close()
            
            self.status.config(text="¡Proceso Terminado!")
            messagebox.showinfo("Hecho", f"Archivos guardados en:\n{self.out_dir}")
            try: os.startfile(self.out_dir)
            except: pass

        except Exception as e:
            messagebox.showerror("Error Crítico", str(e))
        finally:
            self.stop_server()
            self.btn_go.config(state="normal")

    def compress_and_save(self, pdf_bytes, name, quality, max_w, clean_meta):
        doc = fitz.open("pdf", pdf_bytes)
        
        # Optimización de imágenes (Motor V4)
        for page in doc:
            for img in page.get_images():
                xref = img[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n > 4: pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    img_data = pix.tobytes("png")
                    with Image.open(io.BytesIO(img_data)) as pil_img:
                        buffer = io.BytesIO()
                        
                        # Resize
                        if pil_img.width > max_w:
                            ratio = max_w / pil_img.width
                            pil_img = pil_img.resize((max_w, int(pil_img.height * ratio)), Image.Resampling.LANCZOS)
                        
                        # Compress
                        if pil_img.mode == 'RGBA':
                             pil_img.save(buffer, format="PNG", optimize=True)
                        else:
                             if pil_img.mode != "RGB": pil_img = pil_img.convert("RGB")
                             pil_img.save(buffer, format="JPEG", quality=quality, optimize=True)

                        page.replace_image(xref, stream=buffer.getvalue())
                except: pass

        # Limpieza de páginas vacías
        to_del = []
        for i, p in enumerate(doc):
            if not p.get_text().strip() and not p.get_images():
                if i == len(doc)-1: to_del.append(i)
        for i in reversed(to_del): doc.delete_page(i)

        if clean_meta: doc.set_metadata({})

        out_path = os.path.join(self.out_dir, name)
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
            
        doc.save(out_path, garbage=4, deflate=True)
        doc.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = ProPDFGenerator(root)
    root.mainloop()