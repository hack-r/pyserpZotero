#.utils.search_scholar.py
import urllib.parse

# Libraries
from serpapi import GoogleSearch
import json
import pandas as pd


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
