# Libraries
import bibtexparser
import certifi
import datetime
import json
import numpy as np
import os
import pandas as pd
import pycurl
import re
import requests

from bibtexparser.bparser import BibTexParser
from datetime import date
from habanero import Crossref
from io import BytesIO
from pyzotero import zotero
from serpapi import GoogleSearch
from urllib.parse import urlencode

class serpZot:
    """
    :param API_KEY: serpAPI API key
    :type API_KEY: str

    :param ZOT_ID: Zotero user (aka library) Id
    :type ZOT_ID: str

    :param ZOT_KEY: Zotero API key
    :type ZOT_KEY: str
    """
 
    def __init__(self, API_KEY  = "", ZOT_ID = "", ZOT_KEY = ""):
        print("Make sure your Zotero key has write permissions.")
        self.API_KEY = API_KEY
        self.ZOT_ID = ZOT_ID
        self.ZOT_KEY = ZOT_KEY

    # User Parameters
    def search2Zotero(self, TERM = "", MIN_YEAR = ""):
        """
        Search for journal articles and add them to your Zotero library.

        :param TERM: search term for Google Scholar
        :type TERM: str

        :param MIN_YEAR: oldest year to search on
        :type MIN_YEAR: str
        """    

        # Search Parameters 
        params = {
          "api_key": self.API_KEY,
          "device": "desktop",
          "engine": "google_scholar",
          "q": TERM,
          "hl": "en",
          "num": "20",
          "as_ylo": MIN_YEAR
        }

        # Search
        search = GoogleSearch(params)

        # Scrape Results, Extract Result Id's
        json_data = search.get_raw_json()
        data = json.loads(json_data)
        df = pd.json_normalize(data['organic_results'])
        ris = df['result_id']

        # Get the Citation!
        params = {
          "api_key": self.API_KEY,
          "device": "desktop",
          "engine": "google_scholar_cite",
          "q": ris[0]
        }

        search = GoogleSearch(params)
        citation = search.get_dict()

        # Get APA Format Citation and Parse
        citation['citations'][1]['snippet']

        # Cross-reference the Citation with Crossref to Get Bibtext
        base = 'https://api.crossref.org/works?query.'
        api_url = {'bibliographic':citation['citations'][1]['snippet']}
        url = urlencode(api_url)
        url = base+url
        response = requests.get(url)

        # Parse Bibtext from Crossref
        jsonResponse = response.json()
        jsonResponse = jsonResponse['message']
        jsonResponse = jsonResponse['items']
        jsonResponse = jsonResponse[0]
        jsonResponse['DOI']
        curl_str = 'curl -LH "Accept: application/x-bibtex" http://dx.doi.org/' + jsonResponse['DOI']
        result = os.popen(curl_str).read()

        # Write bibtext file
        text_file = open("auto_cite.bib", "w")
        n = text_file.write(result)
        text_file.close()

        # Parse bibtext
        with open('auto_cite.bib') as bibtex_file:
            parser = BibTexParser()
            parser.customization = bibtexparser.customization.author    
            bib_database = bibtexparser.load(bibtex_file, parser=parser)
        bib_dict = bib_database.entries[0]
        print(bib_dict)

        # Connect to Zotero
        zot = zotero.Zotero(self.ZOT_ID, 'user', self.ZOT_KEY)
        template = zot.item_template('journalArticle') # Set Template

        # Populate Zotero Template with Data
        try:
            template['publicationTitle'] = bib_dict['journal']
        except:
            pass
        template['title'] = bib_dict['title']
        template['DOI'] = str(jsonResponse['DOI'])
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
        mydate = bib_dict['month']+' '+bib_dict['year']
        template['date'] = str(datetime.datetime.strptime(mydate, '%b %Y').date())

        # Parse Names into Template/Data
        num_authors = len(bib_dict['author'])
        template['creators'] = []

        for a in bib_dict['author']:
            split = bibtexparser.customization.splitname(a, strict_mode=False)
            template['creators'].append({'creatorType': 'author', 'firstName': split['first'][0], 'lastName': split['last'][0]})

        print(template)

        zot.create_items([template])

        return 0
