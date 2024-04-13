# pyserpZotero.py
import urllib.parse

# Libraries
try:
    from .utils.arxiv_helpers import arxiv_download
except ImportError:
    from utils.arxiv_helpers import arxiv_download
from bibtexparser.bparser import BibTexParser
import threading
from box import Box
from datetime import date, datetime
from pyzotero import zotero
from serpapi import GoogleSearch
from urllib.parse import urlencode
import urllib.request as libreq

import bibtexparser
import json
import os
import pandas as pd
import requests
import re
import time

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
    def __init__(self, serp_api_key="", zot_id="", zot_key="", download_dest=".", enable_pdf_download=True):
        """
        Instantiate a SerpZot object for API management.

        Keep assignment operators reasonably aligned like an R programmer,
            so code doesn't look like PEP dog poo.
        """
        self.df           = None
        self.FIELD        = "title"
        self.DOI_HOLDER   = set()
        self.SERP_API_KEY = ""
        self.ZOT_ID       = ""
        self.ZOT_KEY      = ""
        self.DOWNLOAD_DEST       = ""
        self.enable_pdf_download = ""
        
        # For shared dict
        self.CITATION_DICT = dict()
        self.lock = threading.Lock()
        
        # Override default values with values from config.yaml
        config = Box.from_yaml(filename="config.yaml")

        if not self.SERP_API_KEY:
            config = Box.from_yaml(filename="config.yaml")
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

    def attempt_pdf_download(self, items, full_lib=False):
        """
        Attempt to download a PDF for a specified DOI and attach it to a Zotero item.

        Parameters:
        - items: Collection of Zotero items to consider for download.
        - full_lib (bool): Flag to indicate whether to search the entire library.

        Returns:
        - (bool): 0 after all downloads are done
        """
        # Try to download PDF from various sources
        download_dest = self.DOWNLOAD_DEST
        
        # Running infinite loop
        while(True):
            doi = None
            zotero_item_keys, bib_dict = None, None
            
            try:
                
                print("Entered while loop...")
                with self.lock:
                    if len(self.CITATION_DICT) == 0:
                        print("Empty List... Waiting ", len(self.CITATION_DICT) , "\n\n", self.CITATION_DICT)
                        time.sleep(1)
                        continue
                    
                with self.lock:
                    print("Starting download ----")
                    doi = list(self.CITATION_DICT.keys())[0]
                    
                    # Last key is 'END'
                    if type(doi) == str and doi == "END":
                        print("DONE WITH ALL DOWNLOADS. ENDING.")
                        break
                    
                    zotero_item_keys, bib_dict = self.CITATION_DICT[doi]
                    
                title = bib_dict.get('title')
                    
                print(f"\n\nStarting download for doi: {doi}\nZotero Item Keys: {zotero_item_keys}\nBib Dict: {bib_dict}\n\n")
                                    
                downloaded, pdf_path = arxiv_download(items=items, download_dest=download_dest, doi=doi, full_lib=full_lib, title=title)

                if not downloaded:
                    print(f"No PDF available for doi: {doi}, moving on.")

                # If a PDF was downloaded, attach it to the Zotero item
                if downloaded:
                    for zotero_item_key in zotero_item_keys:
                
                        zot = zotero.Zotero(self.ZOT_ID, 'user', self.ZOT_KEY)
                        if os.path.isfile(pdf_path):
                            zot.attachment_simple([pdf_path], zotero_item_key)
                        else:
                            pdf_path = pdf_path.removeprefix("./")
                            zot.attachment_simple([pdf_path], zotero_item_key)
                    print(f"PDF for {doi} attached successfully.")
                    
                if doi != None:
                    with self.lock:
                        del self.CITATION_DICT[doi]
                                
            except Exception as e:
                print("Exception occurred:\n", e)
                print("Continuing")
                
                if doi != None:
                    with self.lock:
                        del self.CITATION_DICT[doi]
            
                    
        return 0

    # Search for RIS Result ID's on Google Scholar
    def SearchScholar(self, term="", min_year="", save_bib=False):
        """
        Search Google Scholar for articles matching the specified criteria and update Zotero library.

        Parameters:
        - term (str): The search term or query.
        - min_year (str): The earliest publication year for articles.
        - save_bib (bool): Whether to save the search results as a BibTeX file.

        Returns:
        - (int): Status code indicating success (0) or failure (non-zero).
        """


        # Search Parameters
        params = {
            "api_key": self.SERP_API_KEY,
            "device": "desktop",
            "engine": "google_scholar",
            "q": term,
            "hl": "en",
            "num": "20",
            "as_ylo": min_year
        }

        # Search
        search = GoogleSearch(params)

        # Set SAVE_BIB for Search2Zotero
        self.SAVE_BIB = save_bib

        # Scrape Results, Extract Result Id's
        df = pd.DataFrame()  # ignore warning - it gets used
        try:
            json_data = search.get_raw_json()
            data = json.loads(json_data)
            self.df = pd.json_normalize(data['organic_results'])
            df = self.df
            ris = df['result_id']
            self.ris = ris
        except Exception as e:
            print(f"An error occurred while filling into Pandas: {str(e)}")

        return 0

    def processBibsAndUpload( self, doiSet, zot, items, FIELD, citation):
        """
        This function will download pdfs and citations related to all DOIs present in the DOI set. It will also
        upload the results to Zotero

        Parameters:
        - doiSet (set): The set of DOIs.
        - zot (Zotero Object): The place to upload the relevant findings.
        - items (list): List of all present items in Zotero.
        - citation (Boolean): Whether to create citation (True) or to download (False).

        Returns:
        - (int): Status code indicating success (0) or failure (non-zero).
        """
        
        if citation:
            print("Starting citation thread")
            for doi, abstract in doiSet:
                template = zot.item_template('journalArticle')  # Set Template
                curl_str = 'curl -LH "Accept: application/x-bibtex" http://dx.doi.org/' + doi
                result = os.popen(curl_str).read()
                if not result:
                    # medArxiv, bioarxiv and arxiv use this link to get the citation details
                    curl_str = 'curl -LH "Accept: application/x-bibtex" https://doi.org/' + doi
                    result = os.popen(curl_str).read()

                # Write bibtext file
                text_file = open("auto_cite.bib", "w")
                n = text_file.write(result)
                text_file.close()

                if self.SAVE_BIB:
                    # If the user wants we can save a copy of the BIB
                    # that won't be overwritten later
                    dt = datetime.now()
                    ts = datetime.timestamp(dt)
                    fn = "my_bib_" + str(ts) + ".bib"
                    text_file = open(fn, "w")
                    n = text_file.write(result)
                    text_file.close()

                # Parse bibtext
                with open('auto_cite.bib') as bibtex_file:
                    parser = BibTexParser()
                    parser.customization = bibtexparser.customization.author
                    bib_database = bibtexparser.load(bibtex_file, parser=parser)
                try:
                    bib_dict = bib_database.entries[0]
                except Exception as e:
                    print(f"An error occurred: {str(e)}")
                    continue

            # # Parse Names into Template/Data
            # try:
                try:
                    if 'author' not in bib_dict:
                        bib_dict['author'] = ["Unknown, Unknown"]
                except Exception as e:
                    print(f"An error occurred: {str(e)}")
                    continue

                # Populate Zotero Template with Data
                try:
                    template['publicationTitle'] = bib_dict['journal']
                except:
                    pass
                try:
                    template['title'] = bib_dict['title']
                except:
                    pass
                try:
                    template[FIELD] = bib_dict[FIELD]
                except:
                    pass
                try:
                    template['doi'] = str(doi)
                except:
                    pass
                try:
                    template['accessDate'] = str(date.today())
                except:
                    pass
                try:
                    template['extra'] = str(bib_database.comments)
                except:
                    pass
                try:
                    template['url'] = bib_dict['url']
                except:
                    pass
                try:
                    template['volume'] = bib_dict['volume']
                except:
                    pass
                try:
                    template['issue'] = bib_dict['number']
                except:
                    pass
                try:
                    template['abstractNote'] = abstract
                except:
                    pass
                # Fix Date
                try:
                    mydate = bib_dict['month'] + ' ' + bib_dict['year']
                    template['date'] = str(datetime.strptime(mydate, '%b %Y').date())
                except:
                    try:
                        mydate = bib_dict['year']
                        template['date'] = str(bib_dict['year'])
                    except:
                        continue

                # Parse Names into Template/Data
                try:
                    no_author_found = False
                    try:
                        num_authors = len(bib_dict['author'])
                    except:
                        num_authors = 1
                        bib_dict['author'] = ['Unknown Unknown']
                        no_author_found = True
                    template['creators'] = []

                    for a in bib_dict['author']:
                        split = bibtexparser.customization.splitname(a, strict_mode=False)
                        template['creators'].append(
                            {'creatorType': 'author', 'firstName': split['first'][0], 'lastName': split['last'][0]})
                    print(template)
                    if template["doi"] in self.DOI_HOLDER:
                        print("Not citation uploading since it's already present in Zotero")
                        continue
                    if no_author_found:
                        print("No authors found for this paper, skipping upload to zotero")
                        continue
                    if template.get("title", None) == None:
                        print("Paper does not have a title. Skipping upload to Zotero")
                        continue
                    cite_upload_response = zot.create_items([template])
                    zotero_item_key = []
                    if 'successful' in cite_upload_response:
                        for key in cite_upload_response['successful']:
                            zotero_item_key.append(cite_upload_response['successful'][key]['key'])
                    
                    print("ZOTERO ITEM KEYS: ", zotero_item_key)
                    with self.lock:
                        self.CITATION_DICT[doi] = (zotero_item_key, bib_dict)
                        print(f"\n\n\nCITATION DICT: \n{self.CITATION_DICT}")
            
                except Exception as e:
                    print(f"An error occurred while parsing: {e}")
                    
            with self.lock:
                self.CITATION_DICT["END"] = None
        else:
            print("Starting downloading thread")
            full_lib = False
            if self.enable_pdf_download:
                self.attempt_pdf_download(items=items, full_lib=full_lib)
            

        return 0

    # Convert RIS Result ID to Bibtex Citation
    def Search2Zotero(self, query, FIELD="title"):
        """
        Convert search results to Zotero citations, avoiding duplicates, and optionally download PDFs.

        Parameters:
        - FIELD (str): The field of the search result to use, default is 'title'.

        Returns:
        - (int): Status code indicating the operation's success (0) or failure.
        """
        df = pd.DataFrame()

        try:
            df = self.df
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print("Missing a search result dataframe.")

        # Connect to Zotero
        zot = zotero.Zotero(self.ZOT_ID, 'user', self.ZOT_KEY)
        # template = zot.item_template('journalArticle')  # Set Template

        # Retrieve doi numbers of existing articles to avoid duplication of citations
        print("Reading your library's citations so we can avoid adding duplicates...")
        items = zot.everything(zot.items())

        if not self.DOI_HOLDER:  # Populate it only if it's empty
            for item in items:
                try:
                    doi = item["data"].get("doi") or item["data"].get("DOI")
                    if not doi:
                        raise KeyError
                    self.DOI_HOLDER.add(doi)
                except KeyError:
                    try:
                        url = item['data']['url']
                        if url:
                            self.DOI_HOLDER.add(url)
                    except:
                        continue

        try:
            ris = self.ris
            print(f"Number of Google Scholar search results to process : {len(ris)}")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print("No results? Or an API key problem, maybe?")
            print("Fatal error!")
            ris = ""

        # Keep adding all the DOIs we find from all methods to this set, then download them
        # all the end.
        doiSet = set()
        
        # Processing everything we got from SearchScholar
        for i in ris:

            # Announce status
            print(f'Now processing: {i}')

            # Get the Citation from SerpApi search!
            params = {
                "api_key": self.SERP_API_KEY,
                "device": "desktop",
                "engine": "google_scholar_cite",
                "q": i
            }

            search = GoogleSearch(params)
            citation = search.get_dict()

            # Cross-reference the Citation with Crossref to Get Bibtext
            base     = 'https://api.crossref.org/works?query.'
            api_url  = {'bibliographic': citation['citations'][1]['snippet']}
            url      = urlencode(api_url)
            url      = base + url
            response = requests.get(url)

            # Parse Bibtext from Crossref
            try:
                jsonResponse = response.json()
                jsonResponse = jsonResponse['message']
                jsonResponse = jsonResponse['items']
                jsonResponse = jsonResponse[0]
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                continue
            doiSet.add((jsonResponse['DOI'], df['snippet'][0]))


        # arXiv processing of DOIs
        query = urllib.parse.quote_plus(query)
        url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=50"
        r = libreq.urlopen(url).read()
        out = re.findall('http:\/\/dx.doi.org\/[^"]*', str(r))
        arxivCount = 0
        for doiLink in out:
            try:
                doi = doiLink.split("http://dx.doi.org/")[1]
                print("Found doi link", doi)
                arxivCount += 1
                doiSet.add(tuple([doi, None]))
            except:
                print("Wrong Link")
                continue
        print("Number of entries found in arXiv Search: ", arxivCount)

        # TODO search in bioXriv and medXriv

        # For all the DOIs we got using all methods, search citations and add PDFs
        
        # Running citation and download parallely
        citation_thread = threading.Thread(target=self.processBibsAndUpload, args=(doiSet, zot, items, FIELD, True))
        upload_thread = threading.Thread(target=self.processBibsAndUpload, args=(doiSet, zot, items, FIELD, False))
        
        citation_thread.start()
        upload_thread.start()
        
        citation_thread.join()
        upload_thread.join()

        return 0


# ANSI escape codes for colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

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

    script_dir_config_path = Path(__file__).resolve().parent / 'config.yaml'
    current_dir_config_path = Path('.').resolve() / 'config.yaml'

    if current_dir_config_path.is_file():
        config_path = current_dir_config_path
    elif script_dir_config_path.is_file():
        config_path = script_dir_config_path
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
    download_pdfs = config.get('ENABLE_PDF_DOWNLOAD', None)
    if download_pdfs is None:
        download_pdfs = input("Do you want to download PDFs? [Y/n]: ").strip().lower()
    if download_pdfs == '' or download_pdfs == 'y' or download_pdfs == 'Y' or download_pdfs == 'yes' or download_pdfs == 'True':
        download_pdfs = True
    else:
        download_pdfs = False

    min_year = input("Enter the oldest year to search from (leave empty if none): ")
    term_string = input("Enter one or more (max up to 20) search terms/phrases separated by semi-colon(;): ")
    
    terms = term_string.split(";")[:20]
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
        

        serp_zot = SerpZot(serp_api_key, zot_id, zot_key, download_dest, download_pdfs)
        serp_zot.SearchScholar(term, min_year)
        serp_zot.Search2Zotero(term)
    # serp_zot = SerpZot(serp_api_key, zot_id, zot_key, download_dest, download_pdfs)
    # serp_zot.SearchScholar(term, min_year)
    # serp_zot.Search2Zotero(term)

        if download_pdfs:
            print("Attempting to download PDFs...")
        print("Done.")


if __name__ == "__main__":
    main()