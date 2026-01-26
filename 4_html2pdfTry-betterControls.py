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

class PortfolioGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Tarquitet PDF - Panel de Control")
        self.root.geometry("600x750")
        
        self.html_files = []
        self.port = 0
        
        # --- VARIABLES DE CONTROL ---
        self.quality_var = tk.IntVar(value=80)      # Calidad JPEG por defecto
        self.max_width_var = tk.IntVar(value=1600)  # Ancho máx por defecto
        self.clean_meta_var = tk.BooleanVar(value=True) # Limpiar metadatos
        
        self.base_dir = os.path.join(os.getcwd(), "assets", "pdf")
        if not os.path.exists(self.base_dir):
            try: os.makedirs(self.base_dir)
            except: self.base_dir = os.getcwd()
        self.out_dir = self.base_dir
        
        self.build_ui()

    def build_ui(self):
        style = ttk.Style()
        style.configure("Bold.TLabel", font=("Arial", 10, "bold"))
        style.configure("Header.TLabel", font=("Arial", 14, "bold"), foreground="#333")

        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="GENERADOR PDF PROFESIONAL", style="Header.TLabel").pack(pady=(0, 5))
        ttk.Label(frame, text="Control total sobre calidad y resolución", font=("Arial", 9)).pack(pady=(0, 20))
        
        # 1. ARCHIVOS
        lf_files = ttk.LabelFrame(frame, text="1. Archivos y Destino", padding=10)
        lf_files.pack(fill="x", pady=5)
        
        ttk.Button(lf_files, text="Seleccionar HTMLs", command=self.sel_files).pack(fill="x")
        self.lbl_f = ttk.Label(lf_files, text="0 archivos seleccionados", foreground="gray", font=("Arial", 8))
        self.lbl_f.pack(pady=2)
        
        ttk.Button(lf_files, text="Cambiar Carpeta Salida", command=self.sel_dir).pack(fill="x", pady=(5,0))
        self.lbl_d = ttk.Label(lf_files, text=self.out_dir, foreground="blue", font=("Arial", 8))
        self.lbl_d.pack(pady=2)

        # 2. CALIDAD DE IMAGEN
        lf_img = ttk.LabelFrame(frame, text="2. Ajustes de Imagen", padding=10)
        lf_img.pack(fill="x", pady=10)

        # A) Slider Calidad JPEG
        self.lbl_q_val = ttk.Label(lf_img, text=f"Calidad JPEG: {self.quality_var.get()}%")
        self.lbl_q_val.pack(anchor="w")
        ttk.Scale(lf_img, from_=10, to=100, variable=self.quality_var, command=self.update_labels).pack(fill="x", pady=(0, 10))

        # B) Slider Resolución
        self.lbl_w_val = ttk.Label(lf_img, text=f"Resolución Máxima: {self.max_width_var.get()} px")
        self.lbl_w_val.pack(anchor="w")
        ttk.Scale(lf_img, from_=100, to=3000, variable=self.max_width_var, command=self.update_labels).pack(fill="x")
        ttk.Label(lf_img, text="(Afecta a JPEGs y PNGs por igual)", font=("Arial", 8, "italic"), foreground="gray").pack(anchor="e")

        # 3. OPCIONES EXTRA
        lf_opts = ttk.LabelFrame(frame, text="3. Opciones PDF", padding=10)
        lf_opts.pack(fill="x", pady=5)
        
        ttk.Checkbutton(lf_opts, text="Limpiar Metadatos (Privacidad)", variable=self.clean_meta_var).pack(anchor="w")
        ttk.Label(lf_opts, text="* Mantiene enlaces y texto seleccionable", font=("Arial", 8), foreground="gray").pack(anchor="w", padx=20)

        # BOTÓN FINAL
        self.btn_go = ttk.Button(frame, text="GENERAR PDF", state="disabled", command=self.start)
        self.btn_go.pack(pady=20, ipady=10, fill="x")

        self.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x")
        self.status = ttk.Label(frame, text="Esperando...", font=("Arial", 9))
        self.status.pack(pady=5)

    def update_labels(self, _=None):
        q = int(self.quality_var.get())
        w = int(self.max_width_var.get())
        self.lbl_q_val.config(text=f"Calidad JPEG: {q}%")
        self.lbl_w_val.config(text=f"Resolución Máxima: {w} px")

    def sel_files(self):
        files = filedialog.askopenfilenames(filetypes=[("HTML Files", "*.html")])
        if files:
            self.html_files = list(files)
            self.lbl_f.config(text=f"{len(files)} archivos seleccionados", foreground="black")
            self.btn_go.config(state="normal")

    def sel_dir(self):
        d = filedialog.askdirectory(initialdir=self.base_dir)
        if d: 
            self.out_dir = d
            self.lbl_d.config(text=d)

    def start(self):
        threading.Thread(target=self.process_batch, daemon=True).start()

    # --- SERVIDOR LOCAL ---
    def start_server(self, root_dir):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        self.port = sock.getsockname()[1]
        sock.close()
        handler = http.server.SimpleHTTPRequestHandler
        self.httpd = socketserver.TCPServer(("localhost", self.port), handler)
        os.chdir(root_dir)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()

    def stop_server(self):
        if hasattr(self, 'httpd'):
            self.httpd.shutdown()
            self.httpd.server_close()

    def get_smart_name(self, original_path):
        filename = Path(original_path).stem.lower()
        name = "DavidJosuePinto" # PUEDES CAMBIAR ESTO
        
        if "portfolio" in filename or "dossier" in filename or "index" in filename:
            return f"Portfolio_{name}_Multimedia.pdf"
        elif "harvard" in filename:
            return f"CV_{name}_Ingeniero_Multimedia.pdf"
        elif "artistico" in filename:
            return f"CV_{name}_Creative_Developer.pdf"
        else:
            clean = filename.replace("-", "_").title()
            return f"{clean}_{name}.pdf"

    def process_batch(self):
        self.btn_go.config(state="disabled")
        self.progress["maximum"] = len(self.html_files)
        
        # OBTENER VALORES DE LA GUI
        current_quality = int(self.quality_var.get())
        current_max_width = int(self.max_width_var.get())
        do_clean = self.clean_meta_var.get()
        
        project_root = os.path.dirname(self.html_files[0])
        self.start_server(project_root)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                for index, html_path in enumerate(self.html_files):
                    filename = os.path.basename(html_path)
                    final_name = self.get_smart_name(html_path)
                    self.status.config(text=f"Renderizando: {filename}...")
                    
                    page = browser.new_page()
                    page.goto(f"http://localhost:{self.port}/{filename}", wait_until="networkidle")
                    
                    # Auto-scroll
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
                            }, 30);
                        });
                    }""")
                    page.wait_for_timeout(1500) 
                    
                    pdf_bytes = page.pdf(format="A4", print_background=True, margin={"top":"0","bottom":"0","left":"0","right":"0"})
                    page.close()

                    self.status.config(text=f"Optimizando {final_name}...")
                    self.compress_and_save(pdf_bytes, final_name, current_quality, current_max_width, do_clean)
                    self.progress["value"] = index + 1
                
                browser.close()

            self.status.config(text="¡Finalizado con éxito!")
            messagebox.showinfo("Éxito", f"PDFs generados en:\n{self.out_dir}")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            print(e)
        finally:
            self.stop_server()
            self.btn_go.config(state="normal")
            self.progress["value"] = 0

    def compress_and_save(self, pdf_bytes, output_name, quality, max_w, clean_meta):
        doc = fitz.open("pdf", pdf_bytes)
        
        for page_obj in doc:
            for img in page_obj.get_images():
                xref = img[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    
                    # Detectar transparencia
                    if pix.n > 4: pix = fitz.Pixmap(fitz.csRGB, pix)
                    has_alpha = pix.alpha or pix.n > 3 # Canal alpha presente
                    
                    img_data = pix.tobytes("png")
                    
                    with Image.open(io.BytesIO(img_data)) as pil_img:
                        buffer = io.BytesIO()
                        
                        # --- 1. REDIMENSIONADO ---
                        # Aplicamos el límite que pusiste en la ventana a TODAS las imágenes
                        if pil_img.width > max_w:
                            ratio = max_w / pil_img.width
                            pil_img = pil_img.resize((max_w, int(pil_img.height * ratio)), Image.Resampling.LANCZOS)
                        
                        # --- 2. FORMATO INTELIGENTE (SIN REGLA DE TAMAÑO PARA PNG) ---
                        # Si tiene transparencia -> SE RESPETA COMO PNG (sin importar el tamaño)
                        if has_alpha or pil_img.mode == 'RGBA':
                             pil_img.save(buffer, format="PNG", optimize=True)
                        else:
                             # Si es opaca -> JPEG con la calidad del slider
                             if pil_img.mode != "RGB": pil_img = pil_img.convert("RGB")
                             pil_img.save(buffer, format="JPEG", quality=quality, optimize=True)

                        page_obj.replace_image(xref, stream=buffer.getvalue())
                except Exception as e: pass

        # Borrar páginas vacías
        to_delete = []
        for i in range(len(doc)):
            if not doc[i].get_text().strip() and not doc[i].get_images():
                 if i == len(doc) - 1: to_delete.append(i)
        for i in reversed(to_delete): doc.delete_page(i)
        
        # Limpieza de metadatos (según el checkbox)
        if clean_meta:
            doc.set_metadata({}) 

        final_path = os.path.join(self.out_dir, output_name)
        if os.path.exists(final_path):
            try: os.remove(final_path)
            except: pass

        doc.save(final_path, garbage=4, deflate=True)
        doc.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = PortfolioGenerator(root)
    root.mainloop()