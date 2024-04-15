#.utils.search2zotero.py
import threading
from pyzotero import zotero
from serpapi import GoogleSearch
from urllib.parse import urlencode
import urllib.request as libreq

import pandas as pd
import requests
import re
import urllib.parse

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
        base = 'https://api.crossref.org/works?query.'
        api_url = {'bibliographic': citation['citations'][1]['snippet']}
        url = urlencode(api_url)
        url = base + url
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
