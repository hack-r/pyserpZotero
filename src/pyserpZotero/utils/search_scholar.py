#.utils.search_scholar.py

# Libraries
from serpapi import GoogleSearch
import json
import pandas as pd
import requests
from urllib.parse import urlencode
import urllib.request as libreq
import re 


def serpSearch(self, term, min_year, save_bib):
    """
    Searches on medArxiv and returns adds the dois to a list

    Parameters:
    - term (str): The query to search for
    - min_year(int): The year after which the search should be done

    Returns:
    - (list): a list of DOIs
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

    # Set SAVE_BIB for search2_zotero
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


    df = pd.DataFrame()
    doiList = []
    try:
        df = self.df
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Missing a search result dataframe.")


    try:
        ris = self.ris
        print(f"Number of items to process : {len(ris)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("No results? Or an API key problem, maybe?")
        print("Fatal error!")
        ris = ""

    # Processing everything we got from search_scholar
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
        doiList.append((jsonResponse['DOI'], df['snippet'][0]))

    print("Completed SerpApi search! DOIs found:")
    for doi in doiList:
        print(doi)

    return doiList

def searchArxiv( self, query ):
    """
    Searches on arxiv and returns adds the dois to a list

    Parameters:
    - query (str): The query to search for

    Returns:
    - (list): a list of DOIs
    """
    queryList = query.split()
    queryStr = "+".join(queryList)
    doiList = []
    # arXiv processing of DOIs
    url = f"http://export.arxiv.org/api/query?search_query=all:{queryStr}&start=0&max_results=50"
    r = libreq.urlopen(url).read()
    out = re.findall('http:\/\/dx.doi.org\/[^"]*', str(r))
    arxivCount = 0
    for doiLink in out:
        try:
            doi = doiLink.split("http://dx.doi.org/")[1]
            arxivCount += 1
            doiList.append(tuple([doi, None]))
        except Exception as e:
            print("Wrong Link")
            continue
    
    print("Number of entries found in arXiv Search: ", arxivCount)
    for doi in doiList:
        print(doi[0])
    return doiList

def searchMedArxiv(self, query):
    """
    Searches on medArxiv and returns adds the dois to a list

    Parameters:
    - query (str): The query to search for

    Returns:
    - (list): a list of DOIs
    """
    # medxriv link looks like https://www.medrxiv.org/search/humanoid+robot

    queryList = query.split()
    queryStr = "+".join(queryList)
    doiList = []
    medUrl = f"https://www.medrxiv.org/search/{queryStr}"
    response = requests.get(medUrl)

    # process all the DOIs we find
    medDois = re.findall("\/\/doi.org\/([^\s]+)", response.text)

    medArxivCount = 0
    for doi in medDois:
        try:
            medArxivCount += 1
            doiList.append(tuple([doi, None]))
        except Exception as e:
            print("Wrong Link")
            print(e)
            continue
    
    print("Number of entries found in medXriv Search: ", medArxivCount)
    for doi in doiList:
        print(doi[0])

    return doiList

def boiArxivSearch(self, query):
    """
    Searches on bioArxiv and returns adds the dois to a list

    Parameters:
    - query (str): The query to search for

    Returns:
    - (list): a list of DOIs
    """
    # biorxiv link looks like https://www.biorxiv.org/search/breast+Cancer

    queryList = query.split()
    queryStr = "+".join(queryList)
    doiList = []
    bioUrl = f"https://www.biorxiv.org/search/{queryStr}"
    response = requests.get(bioUrl)

    # process all the DOIs we find
    bioDois = re.findall("\/\/doi.org\/([^\s]+)", response.text)

    bioArxivCount = 0
    for doi in bioDois:
        try:
            bioArxivCount += 1
            doiList.append(tuple([doi, None]))
        except Exception as e:
            print("Wrong Link")
            print(e)
            continue

    print("Number of entries found in bioXriv Search: ", bioArxivCount)
    for doi in doiList:
        print(doi[0])
    return doiList


# Search for RIS Result ID's on Google Scholar
def search_scholar(self, term="", min_year="", save_bib=False, download_sources=None):
    """
    Search Google Scholar for articles matching the specified criteria and update Zotero library.

    Parameters:
    - term (str): The search term or query.
    - min_year (str): The earliest publication year for articles.
    - save_bib (bool): Whether to save the search results as a BibTeX file.

    Returns:
    - (int): Status code indicating success (0) or failure (non-zero).
    """

    # Keep adding all the DOIs we find from all methods to this set, then download them
    # all the end.
    doiSet = set()
    if download_sources is None:
        download_sources = {
            "serp": 1,
            "arxiv": 1,
            "medArxiv": 1,
            "bioArxiv": 1,
        }

    if download_sources.get('serp'):
        print("Starting Serp Search")
        serpDoiList = self.serpSearch(term, min_year, save_bib)
        doiSet.update(serpDoiList)

    if download_sources.get('arxiv'):
        arxivSearchResult = self.searchArxiv(term)
        doiSet.update(arxivSearchResult)

    if download_sources.get('medArxiv'):
        medArxivSearchResult = self.searchMedArxiv(term)
        doiSet.update(medArxivSearchResult)

    if download_sources.get('bioArxiv'):
        boiArxivSearchResult = self.boiArxivSearch(term)
        doiSet.update(boiArxivSearchResult)

    self.doiSet = doiSet
    return 0
