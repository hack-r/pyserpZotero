#.utils.search2zotero.py
import threading
from pyzotero import zotero
from serpapi import GoogleSearch
from urllib.parse import urlencode
import urllib.request as libreq

import json
import pandas as pd
import requests
import re
import urllib.parse
try:
    from .arxiv_helpers import *
except:
    from arxiv_helpers import *

# Convert RIS Result ID to Bibtex Citation
def Search2Zotero(self, query, FIELD="title", download_lib=True):
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
    items = []
    if download_lib:
        items = zot.everything(zot.items())
        # col = zot.collections()

        # col_names = ["Arm / Hand Exoskeletons", "Cancer / Tumors"]
        # for itr, col_name in enumerate(col_names):
        #     col_key = ""
        #     for i in col:
        #         if( i.get('data', {}).get('name') == col_name):
        #             col_key = i['key']
        #             break

        #     items = zot.collection_items(col_key)

        #     self.arxiv_download(doi=None, items=items, download_dest=".", full_lib=True, title=None)
        # exit(0)

    else:
        json_data = '''{
            "key": "IHKT6PBN",
            "version": 19315,
            "library": {
                "type": "user",
                self=serp_zot,"id": 7032524,
                "name": "hackr",
                "links": {
                    "alternate": {
                        "href": "https://www.zotero.org/hackr",
                        "type": "text/html"
                    }
                }
            },
            "links": {
                "self": {
                    "href": "https://api.zotero.org/users/7032524/items/IHKT6PBN",
                    "type": "application/json"
                },
                "alternate": {
                    "href": "https://www.zotero.org/hackr/items/IHKT6PBN",
                    "type": "text/html"
                },
                "attachment": {
                    "href": "https://api.zotero.org/users/7032524/items/JL5D29KN",
                    "type": "application/json",
                    "attachmentType": "application/pdf"
                }
            },
            "creators": [
                {"creatorType": "author", "firstName": "Bina", "lastName": "Joe"},
                {"creatorType": "author", "firstName": "Xi", "lastName": "Cheng"}
            ],
            "abstractNote": "",
            "publicationTitle": "Physiological Genomics",
            "volume": "52",
            "issue": "4",
            "pages": "",
            "date": "2020",
            "DOI": "10.1152/physiolgenomics.00029.2020",
            "url": "http://dx.doi.org/10.1152/physiolgenomics.00029.2020",
            "accessDate": "2024-02-24",
            "dateAdded": "2024-02-24T22:53:03Z",
            "dateModified": "2024-02-24T22:53:03Z"
        }'''

        data_dict = json.loads(json_data)
        items = [data_dict]
    if not self.DOI_HOLDER:  # Populate it only if it's empty
        for item in items:
            try:
                doi = item["data"].get("doi") or item["data"].get("DOI")
                if not doi:
                    raise KeyError
                self.DOI_HOLDER.add(doi)
                if item['links'].get('attachment') == None:
                    # This could also be a pdf document.
                    if item['data'].get('parentItem') != None:
                        continue
                    self.downloadAttachment[doi] =  item['key']
            except KeyError:
                try:
                    url = item['data']['url']
                    if url:
                        self.DOI_HOLDER.add(url)
                except:
                    continue

    doiSet = self.doiSet
    citation_thread = threading.Thread(target=self.processBibsAndUpload, args=(doiSet, zot, items, FIELD, True))
    upload_thread = threading.Thread(target=self.processBibsAndUpload, args=(doiSet, zot, items, FIELD, False))

    citation_thread.start()
    upload_thread.start()

    citation_thread.join()
    upload_thread.join()

    return 0
