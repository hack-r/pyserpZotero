import threading
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk
import logging
import yaml

from pathlib import Path

try:
    from pyserpZotero.pyserpZotero import SerpZot
except ImportError:
    # Adjust the import based on your project structure
    from pyserpZotero import SerpZot

# Configure root logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

class TextHandler(logging.Handler):
    """This class allows logging to a Tkinter Text widget."""
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        """

        :param record:
        """
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            # Autoscroll to the end
            self.text_widget.yview(tk.END)
        self.text_widget.after(0, append)

class SerpZotGUI:
    """GUI application for pyserpZotero."""

    def __init__(self, master):
        """Initialize the GUI."""
        self.master = master
        master.title("pyserpZotero GUI")

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

        # Create UI components
        self.create_widgets()

        # Load config if available
        self.load_config()

    def cancel_processing(self):
        """Cancel the ongoing process."""
        if self.processing:
            self.cancelled = True
            logging.info("Cancelling the process...")
        else:
            logging.info("No process to cancel.")

    def create_widgets(self):
        """Create the UI widgets."""
        row = 0
        tk.Label(self.master, text="SerpAPI Key:").grid(row=row, column=0, sticky=tk.W)
        tk.Entry(self.master, textvariable=self.serp_api_key, width=50).grid(row=row, column=1, columnspan=2)
        row += 1

        tk.Label(self.master, text="Zotero Library ID:").grid(row=row, column=0, sticky=tk.W)
        tk.Entry(self.master, textvariable=self.zot_id, width=50).grid(row=row, column=1, columnspan=2)
        row += 1

        tk.Label(self.master, text="Zotero API Key:").grid(row=row, column=0, sticky=tk.W)
        tk.Entry(self.master, textvariable=self.zot_key, width=50).grid(row=row, column=1, columnspan=2)
        row += 1

        tk.Label(self.master, text="Download Destination:").grid(row=row, column=0, sticky=tk.W)
        tk.Entry(self.master, textvariable=self.download_dest, width=50).grid(row=row, column=1)
        tk.Button(self.master, text="Browse", command=self.browse_download_dest).grid(row=row, column=2)
        row += 1

        tk.Checkbutton(self.master, text="Download Zotero Library to Avoid Duplicates", variable=self.download_lib).grid(row=row, column=0, columnspan=3, sticky=tk.W)
        row += 1

        tk.Checkbutton(self.master, text="Download PDFs", variable=self.download_pdfs).grid(row=row, column=0, columnspan=3, sticky=tk.W)
        row += 1

        tk.Label(self.master, text="Oldest Year to Search From:").grid(row=row, column=0, sticky=tk.W)
        tk.Entry(self.master, textvariable=self.min_year).grid(row=row, column=1, columnspan=2)
        row += 1

        tk.Label(self.master, text="Max Number of Searches (1-100):").grid(row=row, column=0, sticky=tk.W)
        tk.Entry(self.master, textvariable=self.max_searches).grid(row=row, column=1, columnspan=2)
        row += 1

        tk.Label(self.master, text="Search Terms (separated by semicolons ';'):").grid(row=row, column=0, sticky=tk.W)
        tk.Entry(self.master, textvariable=self.search_terms, width=50).grid(row=row, column=1, columnspan=2)
        row += 1

        # Buttons
        self.start_button = tk.Button(self.master, text="Start", command=self.start_processing)
        self.start_button.grid(row=row, column=0)
        self.cancel_button = tk.Button(self.master, text="Cancel", command=self.cancel_processing, state='disabled')
        self.cancel_button.grid(row=row, column=1)
        tk.Button(self.master, text="Exit", command=self.master.quit).grid(row=row, column=2)
        row += 1

        # Progress Bar
        self.progress = ttk.Progressbar(self.master, orient='horizontal', mode='determinate')
        self.progress.grid(row=row, column=0, columnspan=3, sticky=tk.W+tk.E)
        row +=1

        # Log Viewer
        tk.Label(self.master, text="Logs:").grid(row=row, column=0, sticky=tk.W)
        row += 1
        self.log_text = tk.Text(self.master, height=15, state='disabled')
        self.log_text.grid(row=row, column=0, columnspan=3)
        row += 1

        # Set up logging handler
        self.text_handler = TextHandler(self.log_text)
        logger = logging.getLogger()
        logger.addHandler(self.text_handler)

    def browse_download_dest(self):
        """Open a dialog to select download destination."""
        directory = filedialog.askdirectory()
        if directory:
            self.download_dest.set(directory)

    def load_config(self):
        """Load configuration from config.yaml if available."""
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

    def start_processing(self):
        """Start the search and download process."""
        # Validate inputs
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

        # Prepare parameters
        terms = [term.strip() for term in self.search_terms.get().split(';') if term.strip()]
        terms = terms[:20]  # Limit to 20 terms

        # Validate min_year
        min_year = self.min_year.get()
        if min_year and not (min_year.isdigit() and len(min_year) == 4):
            messagebox.showerror("Error", "Please enter a valid 4-digit year for 'Oldest Year to Search From'.")
            return

        # Validate max_searches
        max_searches = self.max_searches.get()
        if not (1 <= max_searches <= 100):
            messagebox.showerror("Error", "Max number of searches must be between 1 and 100.")
            return

        # Save config
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

        # Start processing in a new thread to keep UI responsive
        threading.Thread(target=self.process_terms, args=(terms, min_year, max_searches)).start()

    def process_terms(self, terms, min_year, max_searches):
        """Process the search terms."""
        serp_zot = SerpZot(
            serp_api_key=self.serp_api_key.get(),
            zot_id=self.zot_id.get(),
            zot_key=self.zot_key.get(),
            download_dest=self.download_dest.get(),
            enable_pdf_download=self.download_pdfs.get(),
            enable_lib_download=self.download_lib.get()
        )

        downloadSources = {
            "serp": True,
            "arxiv": True,
            "medArxiv": True,
            "bioArxiv": True,
        }

        for term in terms:
            logging.info(f"Searching for: {term}")
            # Call methods on serp_zot instance
            serp_zot.search_scholar(term=term, min_year=min_year, download_sources=downloadSources, max_searches=max_searches)
            serp_zot.search2zotero(query=term, download_lib=self.download_lib.get())

        messagebox.showinfo("Completed", "Processing completed.")

# Main execution
def main():
    """Run the GUI application."""
    root = tk.Tk()
    app = SerpZotGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
