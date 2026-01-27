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

# --- UI SCROLLABLE ---
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self, height=150, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            try: canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except: pass
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

# --- APP PRINCIPAL V10 ---
class ProPDFGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Tarquitet PDF - Manual Control V10")
        self.root.geometry("600x720")
        
        self.file_rows = [] 
        self.port = 0
        self.httpd = None
        
        # --- VARIABLES ---
        self.first_name = tk.StringVar(value="David")
        self.last_name = tk.StringVar(value="Pinto")
        self.role_es = tk.StringVar(value="Ingeniero Multimedia")
        self.role_en = tk.StringVar(value="Multimedia Engineer")
        
        self.naming_pattern = tk.StringVar(value="{Type}_{Name}_{Role}_{Lang}")
        self.separator_char = tk.StringVar(value="_") 
        self.join_words_var = tk.BooleanVar(value=True) 
        
        # Sliders (Variables de control)
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
        style.configure("Title.TLabel", font=("Arial", 12, "bold"))
        style.configure("Small.TLabel", font=("Arial", 8), foreground="#666")
        
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        # HEADER
        header = ttk.Frame(main_frame)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="GENERADOR PDF: CONTROL MANUAL", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="v10", style="Small.TLabel").pack(side="right")

        # --- 1. IDENTIDAD ---
        info_frame = ttk.LabelFrame(main_frame, text="1. Identidad", padding=(10, 5))
        info_frame.pack(fill="x", pady=2)
        
        info_frame.columnconfigure(1, weight=1)
        info_frame.columnconfigure(3, weight=1)
        
        ttk.Label(info_frame, text="Nombre:").grid(row=0, column=0, sticky="w")
        ttk.Entry(info_frame, textvariable=self.first_name).grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Label(info_frame, text="Apellido:").grid(row=0, column=2, sticky="w")
        ttk.Entry(info_frame, textvariable=self.last_name).grid(row=0, column=3, sticky="ew", padx=5)
        
        ttk.Label(info_frame, text="Rol (ES):").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(info_frame, textvariable=self.role_es).grid(row=1, column=1, sticky="ew", padx=5)
        
        ttk.Label(info_frame, text="Rol (EN):").grid(row=1, column=2, sticky="w", pady=5)
        ttk.Entry(info_frame, textvariable=self.role_en).grid(row=1, column=3, sticky="ew", padx=5)

        # --- 2. NOMENCLATURA ---
        name_frame = ttk.LabelFrame(main_frame, text="2. Nomenclatura", padding=(10, 5))
        name_frame.pack(fill="x", pady=2)
        
        r1 = ttk.Frame(name_frame)
        r1.pack(fill="x")
        ttk.Label(r1, text="Patrón:").pack(side="left")
        pat_combo = ttk.Combobox(r1, textvariable=self.naming_pattern, width=28)
        pat_combo['values'] = ["{Type}_{Name}_{Role}", "{Name}_{Type}_{Role}", "CV_{Name}_{Role}", "{Type}_{Role}_{Name}"]
        pat_combo.pack(side="left", padx=5, fill="x", expand=True)
        
        ttk.Label(r1, text="Sep:").pack(side="left")
        ttk.Combobox(r1, textvariable=self.separator_char, width=3, state="readonly", values=["_", "-", " "]).pack(side="left", padx=5)
        
        r2 = ttk.Frame(name_frame)
        r2.pack(fill="x", pady=(5,0))
        ttk.Checkbutton(r2, text="CamelCase (Unir palabras)", variable=self.join_words_var).pack(side="left")
        self.preview_lbl = ttk.Label(r2, text="Ej: ...", foreground="blue", font=("Consolas", 8))
        self.preview_lbl.pack(side="right")
        
        for var in [self.naming_pattern, self.separator_char, self.first_name, 
                    self.last_name, self.role_es, self.join_words_var]:
            var.trace("w", self.update_preview)

        # --- 3. ARCHIVOS ---
        file_frame = ttk.LabelFrame(main_frame, text="3. Archivos HTML", padding=(10, 5))
        file_frame.pack(fill="both", expand=True, pady=2)
        
        btn_f = ttk.Frame(file_frame)
        btn_f.pack(fill="x", pady=(0, 2))
        ttk.Button(btn_f, text="+ Añadir HTMLs", command=self.sel_files).pack(side="left")
        ttk.Button(btn_f, text="Destino...", command=self.sel_dir).pack(side="right")
        
        self.scroll_area = ScrollableFrame(file_frame)
        self.scroll_area.pack(fill="both", expand=True)
        self.lbl_no_files = ttk.Label(self.scroll_area.scrollable_frame, text="Arrastra o selecciona archivos", foreground="gray")
        self.lbl_no_files.pack(pady=10)

        # --- 4. AJUSTES (EDITABLES) ---
        tech_frame = ttk.LabelFrame(main_frame, text="4. Ajustes Técnicos", padding=(10, 5))
        tech_frame.pack(fill="x", pady=2)
        
        sliders_box = ttk.Frame(tech_frame)
        sliders_box.pack(fill="x")
        
        # Columna 1: Calidad
        c1 = ttk.Frame(sliders_box)
        c1.pack(side="left", fill="x", expand=True, padx=(0, 5))
        h1 = ttk.Frame(c1); h1.pack(fill="x")
        ttk.Label(h1, text="Calidad JPG").pack(side="left")
        
        # Entry Calidad (Manual)
        self.ent_qual = ttk.Entry(h1, textvariable=self.quality_var, width=4)
        self.ent_qual.pack(side="right")
        self.ent_qual.bind('<Return>', self.validate_quality)
        self.ent_qual.bind('<FocusOut>', self.validate_quality)
        
        # Slider Calidad
        self.sc_qual = ttk.Scale(c1, from_=10, to=100, variable=self.quality_var, command=self.on_qual_slide)
        self.sc_qual.pack(fill="x")
        
        # Columna 2: Ancho
        c2 = ttk.Frame(sliders_box)
        c2.pack(side="left", fill="x", expand=True, padx=(5, 0))
        h2 = ttk.Frame(c2); h2.pack(fill="x")
        ttk.Label(h2, text="Ancho Max (px)").pack(side="left")
        
        # Entry Ancho (Manual)
        self.ent_width = ttk.Entry(h2, textvariable=self.max_width_var, width=5)
        self.ent_width.pack(side="right")
        self.ent_width.bind('<Return>', self.validate_width)
        self.ent_width.bind('<FocusOut>', self.validate_width)
        
        # Slider Ancho
        self.sc_width = ttk.Scale(c2, from_=500, to=3000, variable=self.max_width_var, command=self.on_width_slide)
        self.sc_width.pack(fill="x")
        
        ttk.Checkbutton(tech_frame, text="Limpiar Metadatos (Privacidad)", variable=self.clean_meta_var).pack(anchor="w", pady=(5,0))

        # --- BOTÓN ---
        self.btn_go = ttk.Button(main_frame, text="GENERAR PDFs", command=self.start, state="disabled")
        self.btn_go.pack(fill="x", pady=(10, 5))
        
        self.status_bar = ttk.Frame(main_frame)
        self.status_bar.pack(fill="x")
        self.progress = ttk.Progressbar(self.status_bar, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True)
        self.status = ttk.Label(self.status_bar, text="Listo", font=("Arial", 8))
        self.status.pack(side="right", padx=5)

    # --- HELPERS UI MEJORADOS (INTELIGENTES) ---
    def on_qual_slide(self, val):
        # Al mover el slider, forzamos que la variable sea ENTERA (sin decimales)
        self.quality_var.set(int(float(val)))

    def on_width_slide(self, val):
        self.max_width_var.set(int(float(val)))

    def validate_quality(self, event=None):
        # Al escribir manual: validar rango y actualizar
        try:
            val = int(self.quality_var.get())
            if val < 10: val = 10
            if val > 100: val = 100
            self.quality_var.set(val)
        except:
            self.quality_var.set(80) # Fallback si escriben letras

    def validate_width(self, event=None):
        try:
            val = int(self.max_width_var.get())
            if val < 100: val = 100
            if val > 4000: val = 4000
            self.max_width_var.set(val)
        except:
            self.max_width_var.set(1600)

    def update_preview(self, *args):
        try:
            ex_name = self.construct_filename(
                "CV", "ES", 
                self.first_name.get(), self.last_name.get(), 
                self.role_es.get(), 
                self.separator_char.get(), 
                self.naming_pattern.get(),
                self.join_words_var.get()
            )
            self.preview_lbl.config(text=f"{ex_name}")
        except: pass

    # --- ARCHIVOS ---
    def sel_files(self):
        files = filedialog.askopenfilenames(filetypes=[("HTML", "*.html")])
        if not files: return
        
        for widget in self.scroll_area.scrollable_frame.winfo_children(): widget.destroy()
        self.file_rows = []
        self.lbl_no_files.pack_forget()
        
        for f_path in files:
            self.add_file_row(f_path)
            
        self.btn_go.config(state="normal")
        self.status.config(text=f"{len(files)} archivos.")

    def add_file_row(self, f_path):
        fname = os.path.basename(f_path)
        row = ttk.Frame(self.scroll_area.scrollable_frame)
        row.pack(fill="x", pady=1, padx=2)
        
        default_type = "Portfolio"
        lower = fname.lower()
        if "cv" in lower or "hoja" in lower or "resume" in lower: default_type = "CV"
        elif "dossier" in lower: default_type = "Dossier"
        elif "carta" in lower: default_type = "Carta"
        
        disp_name = (fname[:25] + '..') if len(fname) > 25 else fname
        ttk.Label(row, text=disp_name, width=25, anchor="w").pack(side="left")
        
        type_var = tk.StringVar(value=default_type)
        cb = ttk.Combobox(row, textvariable=type_var, width=12)
        cb['values'] = ["CV", "Portfolio", "Dossier", "Carta", "Resume", "CoverLetter"]
        cb.pack(side="right")
        
        self.file_rows.append({"path": f_path, "type_var": type_var, "original_name": fname})

    def sel_dir(self):
        d = filedialog.askdirectory(initialdir=self.base_dir)
        if d: self.out_dir = d

    # --- LÓGICA DE NOMBRADO ---
    def clean_str(self, s, sep, do_join):
        s = s.strip()
        if do_join:
            words = re.split(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]', s)
            return "".join([w.title() for w in words if w])
        else:
            clean = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]', sep, s)
            while (sep+sep) in clean: clean = clean.replace(sep+sep, sep)
            return clean

    def construct_filename(self, doc_type, lang, first, last, role, sep, pattern, do_join):
        c_first = self.clean_str(first, sep, do_join)
        c_last = self.clean_str(last, sep, do_join)
        c_role = self.clean_str(role, sep, do_join)
        
        if do_join: c_name = f"{c_first}{c_last}" 
        else: c_name = f"{c_first}{sep}{c_last}"

        name = pattern.replace("{Type}", doc_type)
        name = name.replace("{Name}", c_name)
        name = name.replace("{First}", c_first)
        name = name.replace("{Last}", c_last)
        name = name.replace("{Role}", c_role)
        name = name.replace("{Lang}", lang)
        
        if sep != "_": name = name.replace("_", sep)
        return f"{name}.pdf"

    # --- PROCESO ---
    def start(self):
        threading.Thread(target=self.process, daemon=True).start()

    def start_server(self, root_dir):
        self.stop_server()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        self.port = sock.getsockname()[1]
        sock.close()
        handler = http.server.SimpleHTTPRequestHandler
        self.httpd = socketserver.TCPServer(("localhost", self.port), handler)
        os.chdir(root_dir)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop_server(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None

    def process(self):
        self.btn_go.config(state="disabled")
        self.progress["maximum"] = len(self.file_rows)
        
        first = self.first_name.get()
        last = self.last_name.get()
        role_es = self.role_es.get()
        role_en = self.role_en.get()
        pat = self.naming_pattern.get()
        sep = self.separator_char.get()
        do_join = self.join_words_var.get()
        
        qual = int(self.quality_var.get())
        mw = int(self.max_width_var.get())
        clean = self.clean_meta_var.get()

        if not self.file_rows: return

        project_root = os.path.dirname(self.file_rows[0]["path"])
        self.start_server(project_root)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                
                for idx, item in enumerate(self.file_rows):
                    f_path = item["path"]
                    fname = item["original_name"]
                    
                    is_en = '-en' in fname.lower() or '_en' in fname.lower()
                    lang_code = "EN" if is_en else "ES"
                    curr_role = role_en if is_en else role_es
                    sel_type = item["type_var"].get()
                    
                    final_name = self.construct_filename(
                        sel_type, lang_code, first, last, curr_role, sep, pat, do_join
                    )
                    
                    self.status.config(text=f"Procesando: {final_name}")
                    
                    page = browser.new_page()
                    page.goto(f"http://localhost:{self.port}/{fname}", wait_until="networkidle")
                    
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
                    page.wait_for_timeout(2000)
                    
                    pdf_bytes = page.pdf(format="A4", print_background=True, margin={"top":"0","bottom":"0","left":"0","right":"0"})
                    page.close()
                    
                    self.compress_and_save(pdf_bytes, final_name, qual, mw, clean)
                    self.progress["value"] = idx + 1
                
                browser.close()
            
            self.status.config(text="¡Finalizado!")
            messagebox.showinfo("Éxito", f"PDFs guardados en:\n{self.out_dir}")
            try: os.startfile(self.out_dir)
            except: pass

        except Exception as e:
            messagebox.showerror("Error", str(e))
            print(e)
        finally:
            self.stop_server()
            self.btn_go.config(state="normal")

    def compress_and_save(self, pdf_bytes, name, quality, max_w, clean_meta):
        doc = fitz.open("pdf", pdf_bytes)
        for page in doc:
            for img in page.get_images():
                xref = img[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n > 4: pix = fitz.Pixmap(fitz.csRGB, pix)
                    img_data = pix.tobytes("png")
                    with Image.open(io.BytesIO(img_data)) as pil_img:
                        buffer = io.BytesIO()
                        if pil_img.width > max_w:
                            ratio = max_w / pil_img.width
                            pil_img = pil_img.resize((max_w, int(pil_img.height * ratio)), Image.Resampling.LANCZOS)
                        
                        if pil_img.mode == 'RGBA':
                             pil_img.save(buffer, format="PNG", optimize=True)
                        else:
                             if pil_img.mode != "RGB": pil_img = pil_img.convert("RGB")
                             pil_img.save(buffer, format="JPEG", quality=quality, optimize=True)
                        page.replace_image(xref, stream=buffer.getvalue())
                except: pass

        to_del = []
        for i, p in enumerate(doc):
            if not p.get_text().strip() and not p.get_images():
                if i == len(doc)-1: to_del.append(i)
        for i in reversed(to_del): doc.delete_page(i)

        if clean_meta: doc.set_metadata({})
        
        path = os.path.join(self.out_dir, name)
        if os.path.exists(path):
            try: os.remove(path)
            except: pass
        doc.save(path, garbage=4, deflate=True)
        doc.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = ProPDFGenerator(root)
    root.mainloop()