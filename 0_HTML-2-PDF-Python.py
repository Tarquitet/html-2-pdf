import sys
import os
import subprocess
import threading
import io
import time
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
        self.root.title("Tarquitet PDF Generator (Server Mode)")
        self.root.geometry("600x550")
        self.html_files = []
        self.server_process = None
        self.port = 0
        
        # Configuración de carpetas
        self.base_dir = os.path.join(os.getcwd(), "assets", "pdf")
        if not os.path.exists(self.base_dir):
            try: os.makedirs(self.base_dir)
            except: self.base_dir = os.getcwd()
        
        self.out_dir = self.base_dir
        self.build_ui()

    def build_ui(self):
        frame = ttk.Frame(self.root, padding=25)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="GENERADOR DE DOSSIER & CV", font=("Arial", 14, "bold")).pack(pady=10)
        ttk.Label(frame, text="Modo Servidor Local: Arregla carga de imágenes", font=("Arial", 9)).pack(pady=0)
        
        ttk.Button(frame, text="1. Seleccionar Archivos HTML", command=self.sel_files).pack(fill="x", pady=15)
        self.lbl_f = ttk.Label(frame, text="Esperando selección...", foreground="gray", wraplength=500)
        self.lbl_f.pack(pady=5)

        ttk.Button(frame, text="2. Carpeta de Salida", command=self.sel_dir).pack(fill="x", pady=15)
        self.lbl_d = ttk.Label(frame, text=f"Destino: {self.out_dir}", foreground="#d93025", font=("Arial", 8, "bold"))
        self.lbl_d.pack(pady=5)

        self.btn_go = ttk.Button(frame, text="GENERAR PDFS", state="disabled", command=self.start)
        self.btn_go.pack(pady=30, ipady=15, fill="x")

        self.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=10)

        self.status = ttk.Label(frame, text="Listo", font=("Arial", 9, "italic"))
        self.status.pack()

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
            self.lbl_d.config(text=f"Destino: {d}")

    def start(self):
        threading.Thread(target=self.process_batch, daemon=True).start()

    # --- SERVIDOR LOCAL PARA ARREGLAR IMÁGENES ---
    def start_server(self, root_dir):
        # Busca un puerto libre automáticamente
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        self.port = sock.getsockname()[1]
        sock.close()

        handler = http.server.SimpleHTTPRequestHandler
        self.httpd = socketserver.TCPServer(("localhost", self.port), handler)
        
        # Cambiamos el directorio de trabajo del servidor a la carpeta del proyecto
        os.chdir(root_dir)
        
        print(f"Servidor iniciado en puerto {self.port} en ruta {root_dir}")
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()

    def stop_server(self):
        if hasattr(self, 'httpd'):
            self.httpd.shutdown()
            self.httpd.server_close()

    # --- NOMENCLATURA LIMPIA (SIN FECHAS) ---
    def get_smart_name(self, original_path):
        filename = Path(original_path).stem.lower()
        
        if "portfolio" in filename or "dossier" in filename or "index" in filename:
            return "David_Pinto_Portfolio.pdf"
            
        elif "cv" in filename:
            parts = filename.replace("cv", "").replace("-", " ").replace("_", " ").strip().split()
            cv_type = parts[0].title() if parts else "General"
            if "artistico" in filename: cv_type = "Artistico"
            if "harvard" in filename: cv_type = "Harvard"
            return f"CV_David_Pinto_{cv_type}.pdf"
            
        else:
            return f"{filename.replace('-', '_').title()}.pdf"

    def process_batch(self):
        self.btn_go.config(state="disabled")
        self.progress["maximum"] = len(self.html_files)
        
        # 1. Iniciar servidor en la carpeta donde están los HTMLs
        # Asumimos que todos están en la misma raíz del proyecto
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
                    
                    # 2. CARGAR VÍA LOCALHOST (Esto arregla las imágenes)
                    local_url = f"http://localhost:{self.port}/{filename}"
                    print(f"Cargando: {local_url}")
                    
                    page.goto(local_url, wait_until="networkidle")
                    
                    # 3. AUTO-SCROLL PARA CARGAR IMÁGENES LAZY
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
                                    window.scrollTo(0, 0); // Volver arriba
                                    resolve();
                                }
                            }, 50); // Velocidad de scroll
                        });
                    }""")
                    
                    # Espera extra para asegurar renderizado de fuentes e imágenes
                    page.wait_for_timeout(2000) 
                    
                    # Generar PDF
                    pdf_bytes = page.pdf(
                        format="A4",
                        print_background=True,
                        margin={"top":"0","bottom":"0","left":"0","right":"0"}
                    )
                    page.close()

                    self.status.config(text=f"Comprimiendo: {final_name}...")
                    self.compress_and_save(pdf_bytes, final_name)
                    self.progress["value"] = index + 1
                
                browser.close()

            self.status.config(text="¡Finalizado!")
            messagebox.showinfo("Éxito", f"PDFs generados en:\n{self.out_dir}")
            try: os.startfile(self.out_dir)
            except: pass

        except Exception as e:
            messagebox.showerror("Error", str(e))
            print(e)
        
        finally:
            self.stop_server()
            self.btn_go.config(state="normal")
            self.progress["value"] = 0

    def compress_and_save(self, pdf_bytes, output_name):
        doc = fitz.open("pdf", pdf_bytes)
        
        # Optimización de imágenes
        for page_obj in doc:
            for img in page_obj.get_images():
                xref = img[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n > 4: pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    img_data = pix.tobytes("png")
                    with Image.open(io.BytesIO(img_data)) as pil_img:
                        if pil_img.mode != "RGB": pil_img = pil_img.convert("RGB")
                        
                        # Redimensionar si es muy grande
                        if pil_img.width > 600:
                            ratio = 600 / pil_img.width
                            pil_img = pil_img.resize((600, int(pil_img.height * ratio)), Image.Resampling.LANCZOS)
                        
                        buffer = io.BytesIO()
                        pil_img.save(buffer, format="JPEG", quality=70, optimize=True)
                        page_obj.replace_image(xref, stream=buffer.getvalue())
                except: pass # Si falla una imagen, la deja original

        # Eliminar páginas en blanco (útil para el portafolio si se generó una extra)
        to_delete = []
        for i in range(len(doc)):
            # Si la página tiene muy poco contenido (texto o imagen)
            if not doc[i].get_text().strip() and not doc[i].get_images():
                 # Verificación extra: a veces playwright deja la última hoja vacía
                 if i == len(doc) - 1: to_delete.append(i)
        
        for i in reversed(to_delete):
            doc.delete_page(i)

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