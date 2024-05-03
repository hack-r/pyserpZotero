# .utils.pdf_downloader.py
try:
    from .arxiv_helpers import *
except:
    from arxiv_helpers import *
from pyzotero import zotero
import os
import time

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
    while (True):
        doi = None
        zotero_item_keys, bib_dict = None, None

        try:

            print("Entered while loop...")
            with self.lock:
                if len(self.CITATION_DICT) == 0:
                    print("Empty List... Waiting ", len(self.CITATION_DICT), "\n\n", self.CITATION_DICT)
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

            print(
                f"\n\nStarting download for doi: {doi}\nZotero Item Keys: {zotero_item_keys}\nBib Dict: {bib_dict}\n\n")

            downloaded, pdf_path = self.arxiv_download(items=items, download_dest=download_dest, doi=doi, full_lib=full_lib,
                                                  title=title)

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
