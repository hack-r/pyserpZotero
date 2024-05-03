# pyserpZotero.py

# Libraries
try:
    from .utils.arxiv_helpers import arxiv_download
    from .ui.colors import *
    from .utils.pdf_downloader import *
    from .utils.process_and_upload import *
    from .utils.search_scholar import *
    from .utils.search2zotero import *
except ImportError:
    from utils.arxiv_helpers import arxiv_download
    from ui.colors import *
    from ui.colors import *
    from utils.pdf_downloader import *
    from utils.process_and_upload import *
    from utils.search_scholar import *
    from utils.search2zotero import *
import threading
from box import Box


class SerpZot:
    """
    Initialize a SerpZot instance for managing Zotero citations and PDF downloads.

    Parameters:
    - serp_api_key (str): API key for SerpAPI to perform searches.
    - zot_id (str): Zotero user/library ID for citation management.
    - zot_key (str): API key for accessing Zotero services.
    - download_dest (str): Default directory for downloading PDFs.
    - enable_pdf_download (bool): Flag to enable or disable automatic PDF downloads.
    """
    def __init__(self, serp_api_key="", zot_id="", zot_key="", download_dest=".", enable_pdf_download=True, enable_lib_download=True):
        """
        Instantiate a SerpZot object for API management.

        Keep assignment operators reasonably aligned like an R programmer,
            so code doesn't look like PEP dog poo.
        """
        # Member attributes
        self.df           = None
        self.FIELD        = "title"
        self.DOI_HOLDER   = set()
        self.SERP_API_KEY = ""
        self.ZOT_ID       = ""
        self.ZOT_KEY      = ""
        self.DOWNLOAD_DEST       = ""
        self.enable_pdf_download = ""
        self.enable_lib_download = ""
        self.CITATION_DICT = dict()
        self.downloadAttachment = dict()
        self.lock = threading.Lock()
        self.SAVE_BIB = False

        # Member functions
        SerpZot.processBibsAndUpload = processBibsAndUpload
        SerpZot.SearchScholar = SearchScholar
        SerpZot.Search2Zotero = Search2Zotero
        SerpZot.serpSearch = serpSearch
        SerpZot.searchArxiv = searchArxiv
        SerpZot.boiArxivSearch = boiArxivSearch
        SerpZot.searchMedArxiv = searchMedArxiv
        SerpZot.SearchScholar = SearchScholar
        SerpZot.SearchScholar = SearchScholar
        SerpZot.attempt_pdf_download = attempt_pdf_download
        SerpZot.arxiv_download = arxiv_download

        # Override default values with values from config.yaml
        config = Box.from_yaml(filename="config.yaml")

        if not self.SERP_API_KEY:
            config            = Box.from_yaml(filename="config.yaml")
            self.SERP_API_KEY = config.get('SERP_API_KEY', serp_api_key)
        if not self.ZOT_ID:
            self.ZOT_ID  = config.get('ZOT_ID', zot_id)
        if not self.ZOT_KEY:
            self.ZOT_KEY = config.get('ZOT_KEY', zot_key)
        if not self.DOWNLOAD_DEST:
            self.DOWNLOAD_DEST = config.get('DOWNLOAD_DEST', download_dest)
        if not self.enable_pdf_download:
            self.enable_pdf_download = config.get('ENABLE_PDF_DOWNLOAD', enable_pdf_download)

        print("\nFriendly reminder: Make sure your Zotero key has write permissions. I'm not saying it doesn't, but I can't check it for you.\n")

def main():
    import yaml
    from pathlib import Path

    # Colorful welcome message with version number
    print(f"{Colors.CYAN}        __        __   _                          {Colors.ENDC}")
    print(f"{Colors.CYAN}        \ \      / /__| | ___ ___  _ __ ___   ___ {Colors.ENDC}")
    print(f"{Colors.BLUE}         \ \ /\ / / _ \ |/ __/ _ \| '_ ` _ \ / _ \{Colors.ENDC}")
    print(f"{Colors.BLUE}          \ V  V /  __/ | (_| (_) | | | | | |  __/{Colors.ENDC}")
    print(f"{Colors.CYAN}           \_/\_/ \___|_|\___\___/|_| |_| |_|\___|{Colors.ENDC}")
    print(f"{Colors.GREEN}*********************************************{Colors.ENDC}")
    print(f"{Colors.GREEN}*                                           *{Colors.ENDC}")
    print(f"{Colors.GREEN}*     {Colors.UNDERLINE}Welcome to pyserpZotero Terminal!{Colors.ENDC}     {Colors.GREEN}*")
    print(f"{Colors.GREEN}*                                           *{Colors.ENDC}")
    print(f"{Colors.GREEN}*  Your go-to solution for managing Zotero  *{Colors.ENDC}")
    print(f"{Colors.GREEN}*     entries directly from your terminal.  {Colors.GREEN}*")
    print(f"{Colors.GREEN}*                                           *{Colors.ENDC}")
    print(f"{Colors.GREEN}*{Colors.BLUE}      Version: {Colors.RED}1.1.2{Colors.ENDC}                       {Colors.GREEN}*{Colors.ENDC}")
    print(f"{Colors.GREEN}*********************************************{Colors.ENDC}")

    script_dir_config_path   = Path(__file__).resolve().parent / 'config.yaml'
    current_dir_config_path  = Path('.').resolve() / 'config.yaml'
    current_dir_config_path2 = Path('.').resolve().parent.parent / 'config.yaml'
    print(f"Looking for a config in: {current_dir_config_path}...")
    if current_dir_config_path.is_file():
        print("Found!")
        config_path = current_dir_config_path
    elif current_dir_config_path2.is_file():
        print("...not found.\n")
        print(f"Looking for a config in: {current_dir_config_path2}...")
        config_path = current_dir_config_path2
        print("Found!")
    elif script_dir_config_path.is_file():
        print("... not found.\n")
        print(f"Looking for a config in: {script_dir_config_path}...")
        config_path = script_dir_config_path
        print("Found!")
    else:
        print("Config file not found in script or current directory. Proceeding with provided parameters.")
        return

    if not config_path.is_file():
        print("Config file not found. Creating a new one.")
        with config_path.open('w') as file:
            yaml.dump({'SERP_API_KEY': ''}, file)

    #print(f"Attempting to load configuration from {config_path}")
    with config_path.open('r') as file:
        config = yaml.safe_load(file) or {}

    serp_api_key = config.get('SERP_API_KEY', '')
    if not serp_api_key:
        serp_api_key = input("Enter your serpAPI API key: ")
        with config_path.open('w') as file:
            yaml.dump({'SERP_API_KEY': serp_api_key}, file)
    zot_id = config.get('ZOT_ID', '')
    if not zot_id:
        zot_id = input("Enter your Zotero library ID: ")
    zot_key = config.get('ZOT_KEY', '')
    if not zot_key:
        zot_key = input("Enter your Zotero API key: ")
    download_dest = config.get('DOWNLOAD_DEST', '.')
    if not download_dest:
       download_dest = input("Enter download destination path (leave empty for current directory): ") or "."
    download_lib = config.get('ENABLE_LIB_DOWNLOAD', None)
    if download_lib is None:
        download_lib = input("Do you want to download your citation library to avoid duplicating entries? [Y/n]: ").strip().lower()
        if download_lib == '' or download_lib == 'y' or download_lib == 'Y' or download_lib == 'yes' or download_lib == 'True':
            download_lib = True
        else:
            download_lib = False
    download_pdfs = config.get('ENABLE_PDF_DOWNLOAD', None)
    if download_pdfs is None:
        download_pdfs = input("Do you want to download PDFs? [Y/n]: ").strip().lower()
    if download_pdfs == '' or download_pdfs == 'y' or download_pdfs == 'Y' or download_pdfs == 'yes' or download_pdfs == 'True':
        download_pdfs = True
    else:
        download_pdfs = False
    downloadSources = {
        "serp": 1,
        "arxiv": 1,
        "medArxiv": 1,
        "bioArxiv": 1,
    }
    
    if config.get("NO_SERP"):
        del downloadSources["serp"]
  
    if config.get("NO_ARXIV"):
        del downloadSources["arxiv"]
    
    if config.get("NO_BIOARXIV"):
        del downloadSources["bioArxiv"]

    if config.get("NO_MEDARXIV"):
        del downloadSources["medArxiv"]

    while True:
        min_year = input("Enter the oldest year to search from (leave empty if none): ")
        if min_year == "":
            break
        elif min_year.isdigit() and len(min_year) == 4:
            break
        else:
            print("Please enter a 4-digit year or leave the input blank.")
    term_string = input("Enter one or more (max up to 20) search terms/phrases separated by semi-colon(;): ")
    
    terms      = term_string.split(";")[:20]
    terms_copy = []
    
    # Change terms which have less than 3 characters
    for term in terms:
        t = term
        while len(t) < 3:
            print("Please enter at least 3 characters.")
            t = input("Enter search term for: ")
        terms_copy.append(t)
        
    terms = terms_copy
    
    for term in terms:
        
        # Proceed with using 'term' for Google Scholar search
        print(f"Searching Scholar for: {term}")

        serp_zot = SerpZot(serp_api_key, zot_id, zot_key, download_dest, download_pdfs, enable_lib_download=download_lib)
        serp_zot.SearchScholar( term=term, min_year=min_year, downloadSources = downloadSources)
        serp_zot.Search2Zotero( query=term,
                               download_lib=download_lib)

        if download_pdfs:
            print("Attempting to download PDFs...")
        print("Done.")


if __name__ == "__main__":
    main()