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

# --- AUTO-INSTALADOR DE DEPENDENCIAS ---
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
        self.root.title("Tarquitet PDF Generator (Clean Metadata)")
        self.root.geometry("600x650")
        self.html_files = []
        self.port = 0
        self.quality_var = tk.IntVar(value=75)
        
        self.base_dir = os.path.join(os.getcwd(), "assets", "pdf")
        if not os.path.exists(self.base_dir):
            try: os.makedirs(self.base_dir)
            except: self.base_dir = os.getcwd()
        
        self.out_dir = self.base_dir
        self.build_ui()

    def build_ui(self):
        style = ttk.Style()
        style.configure("Bold.TLabel", font=("Arial", 10, "bold"))

        frame = ttk.Frame(self.root, padding=25)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="GENERADOR DE DOSSIER & CV", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(frame, text="Modo Servidor + Limpieza de Metadatos", font=("Arial", 10)).pack(pady=5)
        
        # 1. ARCHIVOS
        ttk.Label(frame, text="1. Selección de Archivos", style="Bold.TLabel").pack(anchor="w", pady=(20, 5))
        ttk.Button(frame, text="Elegir HTMLs", command=self.sel_files).pack(fill="x")
        self.lbl_f = ttk.Label(frame, text="Ningún archivo seleccionado", foreground="gray")
        self.lbl_f.pack(pady=2)

        # 2. CARPETA
        ttk.Label(frame, text="2. Destino", style="Bold.TLabel").pack(anchor="w", pady=(15, 5))
        ttk.Button(frame, text="Cambiar Carpeta", command=self.sel_dir).pack(fill="x")
        self.lbl_d = ttk.Label(frame, text=f"{self.out_dir}", foreground="#d93025", font=("Arial", 8))
        self.lbl_d.pack(pady=2)

        # 3. CALIDAD
        ttk.Label(frame, text="3. Calidad de Compresión", style="Bold.TLabel").pack(anchor="w", pady=(15, 5))
        
        q_frame = ttk.Frame(frame, borderwidth=1, relief="solid", padding=10)
        q_frame.pack(fill="x")
        
        self.lbl_q_val = ttk.Label(q_frame, text="Calidad: 75% (Estándar)")
        self.lbl_q_val.pack(anchor="w")
        
        self.scale = ttk.Scale(q_frame, from_=10, to=100, variable=self.quality_var, command=self.update_quality)
        self.scale.pack(fill="x", pady=5)
        
        self.lbl_weight = ttk.Label(q_frame, text="Peso Estimado: Medio (~2-5 MB)", foreground="blue")
        self.lbl_weight.pack(anchor="e")

        self.btn_go = ttk.Button(frame, text="GENERAR PDFS LIMPIOS", state="disabled", command=self.start)
        self.btn_go.pack(pady=30, ipady=10, fill="x")

        self.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x")
        self.status = ttk.Label(frame, text="Listo", font=("Arial", 9, "italic"))
        self.status.pack()

    def update_quality(self, val):
        v = int(float(val))
        self.quality_var.set(v)
        
        desc = ""
        weight = ""
        color = "black"

        if v < 40:
            desc = "Baja (Email rápido)"
            weight = "Peso: Muy Ligero (< 1 MB)"
            color = "green"
        elif v < 70:
            desc = "Media (Web/Pantalla)"
            weight = "Peso: Ligero (~1-3 MB)"
            color = "#ccaa00"
        elif v < 85:
            desc = "Alta (Estándar Profesional)"
            weight = "Peso: Medio (~3-8 MB)"
            color = "blue"
        else:
            desc = "Máxima (Impresión)"
            weight = "Peso: Pesado (> 10 MB)"
            color = "red"

        self.lbl_q_val.config(text=f"Calidad: {v}% ({desc})")
        self.lbl_weight.config(text=weight, foreground=color)

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
        name = "David_Pinto"
        
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
        
        project_root = os.path.dirname(self.html_files[0])
        self.start_server(project_root)
        current_quality = self.quality_var.get()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                
                for index, html_path in enumerate(self.html_files):
                    filename = os.path.basename(html_path)
                    final_name = self.get_smart_name(html_path)
                    
                    self.status.config(text=f"Renderizando: {filename}...")
                    
                    page = browser.new_page()
                    local_url = f"http://localhost:{self.port}/{filename}"
                    
                    page.goto(local_url, wait_until="networkidle")
                    
                    # Auto-scroll
                    page.evaluate("""async () => {
                        await new Promise((resolve) => {
                            let totalHeight = 0;
                            const distance = 100;
                            const timer = setInterval(() => {
                                const scrollHeight = document.body.scrollHeight;
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if(totalHeight >= scrollHeight){
                                    clearInterval(timer);
                                    window.scrollTo(0, 0);
                                    resolve();
                                }
                            }, 50);
                        });
                    }""")
                    
                    page.wait_for_timeout(2000) 
                    
                    pdf_bytes = page.pdf(
                        format="A4",
                        print_background=True,
                        margin={"top":"0","bottom":"0","left":"0","right":"0"}
                    )
                    page.close()

                    self.status.config(text=f"Limpiando Metadatos ({current_quality}%)...")
                    self.compress_and_save(pdf_bytes, final_name, current_quality)
                    self.progress["value"] = index + 1
                
                browser.close()

            self.status.config(text="¡Proceso Finalizado!")
            messagebox.showinfo("Éxito", f"Se han generado {len(self.html_files)} archivos limpios en:\n{self.out_dir}")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            print(e)
        
        finally:
            self.stop_server()
            self.btn_go.config(state="normal")
            self.progress["value"] = 0

    def compress_and_save(self, pdf_bytes, output_name, quality_level):
        doc = fitz.open("pdf", pdf_bytes)
        
        # 1. OPTIMIZACIÓN DE IMÁGENES
        for page_obj in doc:
            for img in page_obj.get_images():
                xref = img[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n > 4: pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    img_data = pix.tobytes("png")
                    with Image.open(io.BytesIO(img_data)) as pil_img:
                        if pil_img.mode != "RGB": pil_img = pil_img.convert("RGB")
                        
                        max_w = 1500
                        if quality_level < 50: max_w = 1000
                        if quality_level < 30: max_w = 800

                        if pil_img.width > max_w:
                            ratio = max_w / pil_img.width
                            pil_img = pil_img.resize((max_w, int(pil_img.height * ratio)), Image.Resampling.LANCZOS)
                        
                        buffer = io.BytesIO()
                        # Convertir a JPEG elimina metadatos EXIF internos de la imagen
                        pil_img.save(buffer, format="JPEG", quality=quality_level, optimize=True)
                        page_obj.replace_image(xref, stream=buffer.getvalue())
                except: pass

        # 2. LIMPIEZA DE PÁGINAS VACÍAS
        to_delete = []
        for i in range(len(doc)):
            if not doc[i].get_text().strip() and not doc[i].get_images():
                 if i == len(doc) - 1: to_delete.append(i)
        
        for i in reversed(to_delete):
            doc.delete_page(i)

        # 3. ELIMINACIÓN DE METADATOS DEL PDF
        # Esto borra: Autor, Creador, Título, Subject, Keywords, Fechas de creación/modificación
        doc.set_metadata({}) 

        final_path = os.path.join(self.out_dir, output_name)
        if os.path.exists(final_path):
            try: os.remove(final_path)
            except: pass

        # Guardado con limpieza de basura (garbage=4) y deflación
        doc.save(final_path, garbage=4, deflate=True)
        doc.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = PortfolioGenerator(root)
    root.mainloop()