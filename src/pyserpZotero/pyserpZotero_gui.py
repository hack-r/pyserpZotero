import threading
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import logging
import yaml
from pathlib import Path
from PIL import Image, ImageTk
import fitz  # PyMuPDF

# Import SerpZot
try:
    from pyserpZotero.pyserpZotero import SerpZot
except ImportError:
    from pyserpZotero import SerpZot

# Configure root logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# Import ttkbootstrap for enhanced styling
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *


class TextHandler(logging.Handler):
    """Allows logging to a Tkinter Text widget."""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)

        self.text_widget.after(0, append)


class SerpZotGUI:
    """GUI application for pyserpZotero."""

    def __init__(self, master):
        self.master = master
        master.title("pyserpZotero GUI")

        # Initialize ttkbootstrap style
        self.style = ttkb.Style(theme="litera")
        master.configure(bg=self.style.lookup('TFrame', 'background'))

        # Initialize variables
        self.serp_api_key = tk.StringVar()
        self.zot_id = tk.StringVar()
        self.zot_key = tk.StringVar()
        self.download_dest = tk.StringVar(value=str(Path('.').resolve()))
        self.download_lib = tk.BooleanVar(value=True)
        self.download_pdfs = tk.BooleanVar(value=True)
        self.min_year = tk.StringVar()
        self.max_searches = tk.IntVar(value=50)
        self.search_terms = tk.StringVar()

        self.cancelled = False
        self.processing = False

        # Initialize instance attributes
        self.start_button = None
        self.cancel_button = None
        self.progress = None
        self.log_text = None
        self.text_handler = None
        self.pdf_viewer = None

        # Create UI components
        self.create_widgets()

        # Load config if available
        self.load_config()

    def load_config(self):
        config_paths = [
            Path('.').resolve() / 'config.yaml',
            Path(__file__).resolve().parent / 'config.yaml'
        ]
        for config_path in config_paths:
            if config_path.is_file():
                with config_path.open('r') as file:
                    config = yaml.safe_load(file) or {}
                self.serp_api_key.set(config.get('SERP_API_KEY', ''))
                self.zot_id.set(config.get('ZOT_ID', ''))
                self.zot_key.set(config.get('ZOT_KEY', ''))
                self.download_dest.set(config.get('DOWNLOAD_DEST', str(Path('.').resolve())))
                self.download_lib.set(config.get('ENABLE_LIB_DOWNLOAD', True))
                self.download_pdfs.set(config.get('ENABLE_PDF_DOWNLOAD', True))
                break

    def browse_download_dest(self):
        directory = filedialog.askdirectory()
        if directory:
            self.download_dest.set(directory)

    def start_processing(self):
        if not self.serp_api_key.get():
            messagebox.showerror("Error", "SerpAPI Key is required.")
            return
        if not self.zot_id.get():
            messagebox.showerror("Error", "Zotero Library ID is required.")
            return
        if not self.zot_key.get():
            messagebox.showerror("Error", "Zotero API Key is required.")
            return
        if not self.search_terms.get():
            messagebox.showerror("Error", "At least one search term is required.")
            return

        terms = [term.strip() for term in self.search_terms.get().split(';') if term.strip()]
        terms = terms[:20]

        min_year = self.min_year.get()
        if min_year and not (min_year.isdigit() and len(min_year) == 4):
            messagebox.showerror("Error", "Please enter a valid 4-digit year for 'Oldest Year to Search From'.")
            return

        max_searches = self.max_searches.get()
        if not (1 <= max_searches <= 100):
            messagebox.showerror("Error", "Max number of searches must be between 1 and 100.")
            return

        config = {
            'SERP_API_KEY': self.serp_api_key.get(),
            'ZOT_ID': self.zot_id.get(),
            'ZOT_KEY': self.zot_key.get(),
            'DOWNLOAD_DEST': self.download_dest.get(),
            'ENABLE_LIB_DOWNLOAD': self.download_lib.get(),
            'ENABLE_PDF_DOWNLOAD': self.download_pdfs.get(),
        }
        with open('config.yaml', 'w') as file:
            yaml.dump(config, file)

        self.processing = True
        self.cancelled = False
        self.start_button['state'] = 'disabled'
        self.cancel_button['state'] = 'normal'
        threading.Thread(target=self.process_terms, args=(terms, min_year, max_searches)).start()

    def cancel_processing(self):
        if self.processing:
            self.cancelled = True
            logging.info("Cancelling the process...")
        else:
            logging.info("No process to cancel.")

    def process_terms(self, terms, min_year, max_searches):
        serp_zot = SerpZot(
            serp_api_key=self.serp_api_key.get(),
            zot_id=self.zot_id.get(),
            zot_key=self.zot_key.get(),
            download_dest=self.download_dest.get(),
            enable_pdf_download=self.download_pdfs.get(),
            enable_lib_download=self.download_lib.get()
        )

        download_sources = {
            "serp": True,
            "arxiv": True,
            "medArxiv": True,
            "bioArxiv": True,
        }

        total_terms = len(terms)
        for index, term in enumerate(terms):
            if self.cancelled:
                logging.info("Process cancelled by user.")
                break

            logging.info(f"Searching for: {term}")
            serp_zot.search_scholar(term=term, min_year=min_year, download_sources=download_sources, max_searches=max_searches)
            serp_zot.search2zotero(query=term, download_lib=self.download_lib.get())

            progress_value = ((index + 1) / total_terms) * 100
            self.progress['value'] = progress_value
            self.master.update_idletasks()

        if not self.cancelled:
            logging.info("Processing completed.")
            messagebox.showinfo("Completed", "Processing completed.")
        else:
            logging.info("Processing was cancelled.")
            messagebox.showinfo("Cancelled", "Processing was cancelled.")

        self.cancel_button['state'] = 'disabled'
        self.start_button['state'] = 'normal'
        self.processing = False

    def create_widgets(self):
        # Create main frame with padding
        main_frame = ttkb.Frame(self.master, padding=(10, 10, 10, 10))
        main_frame.pack(fill='both', expand=True)

        # Configure grid
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(12, weight=1)

        row = 0

        # Add Image at the top
        try:
            img = Image.open("feature_header.png")
            img = img.resize((400, 100))
            img = ImageTk.PhotoImage(img)
            img_label = ttkb.Label(main_frame, image=img)
            img_label.image = img
            img_label.grid(row=row, column=0, columnspan=3, pady=10)
        except FileNotFoundError:
            logging.warning("Image file not found. Skipping image display.")
            img_label = ttkb.Label(main_frame, text="pyserpZotero", font=("Helvetica", 16))
            img_label.grid(row=row, column=0, columnspan=3, pady=10)

        row += 1

        # SerpAPI Key Input
        ttkb.Label(main_frame, text="SerpAPI Key:").grid(row=row, column=0, sticky=tk.E, padx=5, pady=5)
        ttkb.Entry(main_frame, textvariable=self.serp_api_key).grid(row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=5)

        row += 1

        # Zotero Library ID Input
        ttkb.Label(main_frame, text="Zotero Library ID:").grid(row=row, column=0, sticky=tk.E, padx=5, pady=5)
        ttkb.Entry(main_frame, textvariable=self.zot_id).grid(row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=5)

        row += 1

        # Zotero API Key Input
        ttkb.Label(main_frame, text="Zotero API Key:").grid(row=row, column=0, sticky=tk.E, padx=5, pady=5)
        ttkb.Entry(main_frame, textvariable=self.zot_key).grid(row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=5)

        row += 1

        # Download Destination Input
        ttkb.Label(main_frame, text="Download Destination:").grid(row=row, column=0, sticky=tk.E, padx=5, pady=5)
        ttkb.Entry(main_frame, textvariable=self.download_dest).grid(row=row, column=1, sticky='ew', padx=5, pady=5)
        ttkb.Button(main_frame, text="Browse", command=self.browse_download_dest).grid(row=row, column=2, padx=5, pady=5)

        row += 1

        # Additional Options
        ttkb.Checkbutton(main_frame, text="Download Zotero Library to Avoid Duplicates", variable=self.download_lib).grid(row=row, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        row += 1

        ttkb.Checkbutton(main_frame, text="Download PDFs", variable=self.download_pdfs).grid(row=row, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        row += 1

        # Search Term and Year Inputs
        ttkb.Label(main_frame, text="Oldest Year to Search From:").grid(row=row, column=0, sticky=tk.E, padx=5, pady=5)
        ttkb.Entry(main_frame, textvariable=self.min_year).grid(row=row, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        row += 1

        ttkb.Label(main_frame, text="Max Number of Searches (1-100):").grid(row=row, column=0, sticky=tk.E, padx=5, pady=5)
        ttkb.Entry(main_frame, textvariable=self.max_searches).grid(row=row, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        row += 1

        ttkb.Label(main_frame, text="Search Terms (separated by semicolons ';'):", wraplength=200).grid(row=row, column=0, sticky='ne', padx=5, pady=5)
        ttkb.Entry(main_frame, textvariable=self.search_terms).grid(row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=5)
        row += 1

        # Buttons
        button_frame = ttkb.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)

        self.start_button = ttkb.Button(button_frame, text="Start", command=self.start_processing, bootstyle=SUCCESS)
        self.start_button.pack(side='left', padx=5)

        self.cancel_button = ttkb.Button(button_frame, text="Cancel", command=self.cancel_processing, state='disabled', bootstyle=DANGER)
        self.cancel_button.pack(side='left', padx=5)

        ttkb.Button(button_frame, text="Exit", command=self.master.quit, bootstyle=SECONDARY).pack(side='left', padx=5)
        row += 1

        # Progress Bar
        self.progress = ttkb.Progressbar(main_frame, orient='horizontal', mode='determinate')
        self.progress.grid(row=row, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        row += 1

        # Log Viewer
        ttkb.Label(main_frame, text="Logs:").grid(row=row, column=0, sticky='nw', padx=5, pady=5)
        row += 1

        self.log_text = tk.Text(main_frame, height=15, state='disabled')
        self.log_text.grid(row=row, column=0, columnspan=3, sticky='nsew', padx=5, pady=5)
        main_frame.rowconfigure(row, weight=1)

        # PDF Viewer Button
        ttkb.Button(main_frame, text="Open PDF Viewer", command=self.open_pdf_viewer, bootstyle=INFO).grid(row=row+1, column=0, columnspan=3, pady=5)

        # Set up logging handler
        self.text_handler = TextHandler(self.log_text)
        logger = logging.getLogger()
        logger.addHandler(self.text_handler)

    def open_pdf_viewer(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            viewer = tk.Toplevel(self.master)
            viewer.title(f"PDF Viewer - {Path(file_path).name}")
            viewer.geometry("800x600")

            canvas = tk.Canvas(viewer)
            canvas.pack(fill='both', expand=True)

            doc = fitz.open(file_path)
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                photo = ImageTk.PhotoImage(img)

                canvas.create_image(0, page_num * pix.height, anchor='nw', image=photo)
                canvas.image = photo  # Keep a reference

            viewer.mainloop()


def main():
    root = ttkb.Window(themename="litera")
    app = SerpZotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
