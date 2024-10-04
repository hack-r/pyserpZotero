# .utils.search_scholar.py
"""
Search Scholar and free journal article sources
"""

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from serpapi import GoogleSearch
from urllib.parse import urlencode
import logging
import pandas as pd
import re
import requests
import sys
import urllib.request as libreq
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')


def serpSearch(self, term, min_year, save_bib, max_searches):
    """
    Searches on Google Scholar and returns a list of DOIs.

    Parameters:
    - term (str): The query to search for.
    - min_year (int): The year after which the search should be done.
    - save_bib (bool): Whether to save the BibTeX entries.
    - max_searches (int): Maximum number of search results to retrieve.

    Returns:
    - list: A list of tuples containing DOIs and abstracts.
    """

    # Validate API Key
    if not self.SERP_API_KEY:
        logging.error("SerpAPI key is missing. Please set your API key at https://serpapi.com/manage-api-key")
        sys.exit(1)  # Exit the script gracefully

    # Search Parameters
    results_per_page = 20  # Maximum number of results per page allowed by SerpAPI
    start = 0  # Start index for pagination
    total_results = min(max_searches, 100)  # Limit to 100 as per SerpAPI's restrictions
    doiList = []

    while start < total_results:
        # Adjust results_per_page for the last page
        num_results = min(results_per_page, total_results - start)

        params = {
            "api_key": self.SERP_API_KEY,
            "device": "desktop",
            "engine": "google_scholar",
            "q": term,
            "hl": "en",
            "start": str(start),
            "num": num_results,
            "as_ylo": min_year
        }
        logging.info(f"Searching Google Scholar with parameters: {params}")
        start += num_results

        # Search
        search = GoogleSearch(params)
        self.SAVE_BIB = save_bib

        # Scrape Results, Extract Result Id's
        df = pd.DataFrame()  # ignore warning - it gets used
        try:
            data = search.get_dict()
            if 'error' in data:
                logging.error(f"SerpAPI Error: {data['error']}")
                sys.exit(1)  # Exit for SerpAPI errors

            organic_results = data.get('organic_results', [])
            if not organic_results:
                logging.info("No results found.")
                break

            df = pd.json_normalize(organic_results)
            if self.df.empty:
                self.df = df
            else:
                self.df = pd.concat([self.df, df], ignore_index=True)
            ris = df['result_id']
            self.ris = ris
        except Exception as e:
            logging.exception(f"An error occurred while processing search results: {e}")
            continue

    try:
        df = self.df
        ris = self.ris
        logging.info(f"Number of items to process: {len(ris)}")
    except AttributeError as e:
        logging.info(e)
        logging.error("No results found or an error occurred during the search.")
        sys.exit(1)

    # Processing everything we got from search_scholar
    for i in ris:
        # Announce status
        logging.info(f'Now processing: {i}')

        # Get the Citation from SerpApi search
        params = {
            "api_key": self.SERP_API_KEY,
            "device": "desktop",
            "engine": "google_scholar_cite",
            "q": i
        }

        search = GoogleSearch(params)
        citation = search.get_dict()

        # Cross-reference the Citation with Crossref to Get Bibtex
        base = 'https://api.crossref.org/works?query.'
        api_url = {'bibliographic': citation['citations'][1]['snippet']}
        url = base + urlencode(api_url)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logging.exception(f"Failed to get Crossref data: {e}")
            continue

        # Parse Bibtex from Crossref
        try:
            jsonResponse = response.json()['message']['items'][0]
            doiList.append((jsonResponse['DOI'], df['snippet'][0]))
        except Exception as e:
            logging.exception(f"An error occurred while parsing Crossref response: {e}")
            continue

    logging.info("Completed SerpApi search! DOIs found:")
    for doi in doiList:
        logging.info(doi)

    return doiList


def searchArxiv(self, query):
    """
    Searches on arXiv and returns a list of DOIs.

    Parameters:
    - query (str): The query to search for.

    Returns:
    - list: A list of DOIs.
    """
    queryList = query.split()
    queryStr = "+".join(queryList)
    doiList = []
    # arXiv processing of DOIs
    url = f"http://export.arxiv.org/api/query?search_query=all:{queryStr}&start=0&max_results=50"
    try:
        r = libreq.urlopen(url, timeout=10).read()
        out = re.findall(r'<id>http://arxiv\.org/abs/(.*?)</id>', r.decode('utf-8'))
        arxivCount = 0
        for identifier in out:
            arxivCount += 1
            doiList.append((identifier, None))
        logging.info(f"Number of entries found in arXiv Search: {arxivCount}")
    except Exception as e:
        logging.exception(f"Error occurred during arXiv search: {e}")
    return doiList


def searchMedArxiv(self, query):
    """
    Searches on medRxiv and returns a list of DOIs.

    Parameters:
    - query (str): The query to search for.

    Returns:
    - list: A list of DOIs.
    """
    queryList = query.split()
    queryStr = "+".join(queryList)
    doiList = []
    medUrl = f"https://www.medrxiv.org/search/{queryStr}%20numresults%3A10%20sort%3Arelevance-rank"
    try:
        response = requests.get(medUrl, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.exception(f"Failed to fetch medRxiv search results: {e}")
        return doiList

    # Process all the DOIs we find
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=re.compile(r'^/content/'))
    medArxivCount = 0
    for link in links:
        href = link.get('href')
        match = re.search(r'/content/(.*v\d+)$', href)
        if match:
            doi = match.group(1)
            medArxivCount += 1
            doiList.append((doi, None))

    logging.info(f"Number of entries found in medRxiv Search: {medArxivCount}")
    return doiList


def bioArxivSearch(self, query):
    """
    Searches on bioRxiv and returns a list of DOIs.

    Parameters:
    - query (str): The query to search for.

    Returns:
    - list: A list of DOIs.
    """
    queryList = query.split()
    queryStr = "+".join(queryList)
    doiList = []
    bioUrl = f"https://www.biorxiv.org/search/{queryStr}%20numresults%3A10%20sort%3Arelevance-rank"
    try:
        response = requests.get(bioUrl, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.exception(f"Failed to fetch bioRxiv search results: {e}")
        return doiList

    # Process all the DOIs we find
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=re.compile(r'^/content/'))
    bioArxivCount = 0
    for link in links:
        href = link.get('href')
        match = re.search(r'/content/(.*v\d+)$', href)
        if match:
            doi = match.group(1)
            bioArxivCount += 1
            doiList.append((doi, None))

    logging.info(f"Number of entries found in bioRxiv Search: {bioArxivCount}")
    return doiList


# Search for RIS Result ID's on Google Scholar
def search_scholar(self, term="", min_year=None, download_sources=None, max_searches=50):
    results_list = []
    page = 0
    max_retries = 5
    retries = 0

    while len(results_list) < max_searches and retries < max_retries:
        params = {
            "api_key": self.SERP_API_KEY,
            "engine": "google_scholar",
            "q": term,
            "start": page * 10,
            "as_ylo": min_year,
        }
        response = requests.get("https://serpapi.com/search", params=params)
        if response.status_code == 200:
            data = response.json()
            organic_results = data.get("organic_results", [])
            if organic_results:
                results_list.extend(organic_results)
                page += 1
                retries = 0  # Reset retries if successful
            else:
                retries += 1
                time.sleep(2)
        else:
            print(f"Error: {response.status_code} - {response.text}")
            retries += 1
            time.sleep(2)

    if retries == max_retries:
        print("Max retries reached. Exiting search.")
