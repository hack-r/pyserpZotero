# pyserpZotero.py

# Libraries
from .utils.arxiv_helpers import arxiv_download
from bibtexparser.bparser import BibTexParser
from box import Box
from datetime import date, datetime
from pyzotero import zotero
from serpapi import GoogleSearch
from urllib.parse import urlencode

import bibtexparser
import json
import os
import pandas as pd
import requests


class SerpZot:
    """
    Initialize a SerpZot instance for managing Zotero citations and PDF downloads.

    Parameters:
    - api_key (str): API key for SerpAPI to perform searches.
    - zot_id (str): Zotero user/library ID for citation management.
    - zot_key (str): API key for accessing Zotero services.
    - download_dest (str): Default directory for downloading PDFs.
    - enable_pdf_download (bool): Flag to enable or disable automatic PDF downloads.
    """
    def __init__(self, api_key="", zot_id="", zot_key="", download_dest=".", enable_pdf_download=True):
        """
        Instantiate a SerpZot object for API management.

        Keep assignment operators reasonably aligned like an R programmer,
            so code doesn't look like PEP dog poo.
        """
        self.df         = None
        self.FIELD      = "title"
        self.DOI_HOLDER = set()
        self.API_KEY    = ""
        self.ZOT_ID     = ""
        self.ZOT_KEY    = ""
        self.DOWNLOAD_DEST       = ""
        self.enable_pdf_download = ""

        # Override default values with values from config.yaml
        print(f"Attempting to load configuration from config.yaml")
        config = Box.from_yaml(filename="config.yaml")
        print(config)
        if not self.API_KEY:
            self.API_KEY = config.get('API_KEY', api_key)
        if not self.ZOT_ID:
            self.ZOT_ID  = config.get('ZOT_ID', zot_id)
        if not self.ZOT_KEY:
            self.ZOT_KEY = config.get('ZOT_KEY', zot_key)
        if not self.DOWNLOAD_DEST:
            self.DOWNLOAD_DEST = config.get('DOWNLOAD_DEST', download_dest)
        if not self.enable_pdf_download:
            self.enable_pdf_download = config.get('ENABLE_PDF_DOWNLOAD', enable_pdf_download)

        print("\nFriendly reminder: Make sure your Zotero key has write permissions. I'm not saying it doesn't, but I can't check it for you.\n")

    def attempt_pdf_download(self, items, doi, zotero_item_key, full_lib=False,
                             title=None):
        """
        Attempt to download a PDF for a specified DOI and attach it to a Zotero item.

        Parameters:
        - items: Collection of Zotero items to consider for download.
        - doi (str): The DOI of the paper to download.
        - zotero_item_key (str): The Zotero item key where the PDF should be attached.
        - full_lib (bool): Flag to indicate whether to search the entire library.
        - title (str, optional): The title of the paper, used if DOI is not available.

        Returns:
        - (bool): True if the PDF was successfully downloaded and attached, False otherwise.
        """
        # Try to download PDF from various sources
        download_dest = self.DOWNLOAD_DEST
        downloaded, pdf_path = arxiv_download(items=items, download_dest=download_dest, doi=doi, full_lib=full_lib, title=title)

        if not downloaded:
            print(f"No PDF available for doi: {doi}, moving on.")

        # If a PDF was downloaded, attach it to the Zotero item
        if downloaded:
            zot = zotero.Zotero(self.ZOT_ID, 'user', self.ZOT_KEY)
            if os.path.isfile(pdf_path):
                zot.attachment_simple([pdf_path], zotero_item_key)
            else:
                pdf_path = pdf_path.removeprefix("./")
                zot.attachment_simple([pdf_path], zotero_item_key)
            return True
        return False

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
            "api_key": self.API_KEY,
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

    # Convert RIS Result ID to Bibtex Citation
    def Search2Zotero(self, FIELD="title"):
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
        template = zot.item_template('journalArticle')  # Set Template

        # Retrieve doi numbers of existing articles to avoid duplication of citations
        print("Reading your library's citations so we can avoid adding duplicates...")
        items0 = zot.everything(zot.items(q='doi'))
        items1 = zot.everything(zot.items(q='doi'))
        items  = items0 + items1

        if not self.DOI_HOLDER:  # Populate it only if it's empty
            for item in items:
                try:
                    self.DOI_HOLDER.add(item['data']['doi'])
                except KeyError:
                    try:
                        self.DOI_HOLDER.add(item['data']['url'])
                    except:
                        continue

        try:
            ris = self.ris
            print(f"Number of items to process : {len(ris)}")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print("No results? Or an API key problem, maybe?")
            print("Fatal error!")
            ris = ""

        for i in ris:
            # Announce status
            print(f'Now processing: {i}')

            # Get the Citation!
            params = {
                "api_key": self.API_KEY,
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
            curl_str = 'curl -LH "Accept: application/x-bibtex" http://dx.doi.org/' + jsonResponse['DOI']
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
                template['doi'] = str(jsonResponse['DOI'])
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
                template['abstractNote'] = df['snippet'][0]
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
                try:
                    num_authors = len(bib_dict['author'])
                except:
                    num_authors = 1
                    bib_dict['author'] = ['Unknown Unknown']
                template['creators'] = []

                for a in bib_dict['author']:
                    split = bibtexparser.customization.splitname(a, strict_mode=False)
                    template['creators'].append(
                        {'creatorType': 'author', 'firstName': split['first'][0], 'lastName': split['last'][0]})

                print(template)

                cite_upload_response = zot.create_items([template])
                if 'successful' in cite_upload_response:
                    for key in cite_upload_response['successful']:
                        created_item_key = cite_upload_response['successful'][key]['key']
                        if self.enable_pdf_download:
                            try:
                                print(bib_dict['title'])
                                download_success = self.attempt_pdf_download(items=items,  doi=jsonResponse['DOI'], zotero_item_key=created_item_key,
                                 title=bib_dict['title'])
                            except:
                                download_success = self.attempt_pdf_download(items=items, doi=jsonResponse['DOI'],zotero_item_key=created_item_key,                      title='')
                            if download_success:
                                print(f"PDF for doi {jsonResponse['DOI']} downloaded and attached successfully.")
                            else:
                                print(f"Failed to download PDF for doi {jsonResponse['DOI']}.")

            except Exception as e:
                print(f"An error occurred while parsing: {e}")
                continue

        return 0



def main():
    import yaml
    from pathlib import Path

    script_dir_config_path = Path(__file__).resolve().parent / 'config.yaml'
    current_dir_config_path = Path('.').resolve() / 'config.yaml'

    if script_dir_config_path.is_file():
        config_path = script_dir_config_path
    elif current_dir_config_path.is_file():
        config_path = current_dir_config_path
    else:
        print("Config file not found in script or current directory. Proceeding with provided parameters.")
        return

    if not config_path.is_file():
        print("Config file not found. Creating a new one.")
        with config_path.open('w') as file:
            yaml.dump({'API_KEY': ''}, file)

    print(f"Attempting to load configuration from {config_path}")
    with config_path.open('r') as file:
        config = yaml.safe_load(file) or {}

    api_key = config.get('API_KEY', '')
    if not api_key:
        api_key = input("Enter your serpAPI API key: ")
        with config_path.open('w') as file:
            yaml.dump({'API_KEY': api_key}, file)
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

    term = input("Enter search term for Google Scholar: ")
    min_year = input("Enter the oldest year to search from (leave empty if none): ")

    serp_zot = SerpZot(api_key, zot_id, zot_key, download_dest, download_pdfs)
    serp_zot.SearchScholar(term, min_year)
    serp_zot.Search2Zotero()

    if download_pdfs:
        print("Attempting to download PDFs...")

    print("Done.")


if __name__ == "__main__":
    main()