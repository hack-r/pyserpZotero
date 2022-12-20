## To do: 
# 1. Make this into a proper Python library
# 2. Make a non-Zotero-specific version
# 3. Add other formats, support for middle initials / suffixes 

# Libraries
from bibtexparser.bparser import BibTexParser
from bs4 import BeautifulSoup
from datetime import date
from habanero import Crossref
from io import BytesIO
from pyzotero import zotero
from serpapi import GoogleSearch
from urllib.parse import urlencode

import bibtexparser
import datetime
import json
import numpy as np
import os
import pandas as pd
import re
import requests


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
        print("Reminder: Make sure your Zotero key has write permissions.")
        self.API_KEY = API_KEY
        self.ZOT_ID = ZOT_ID
        self.ZOT_KEY = ZOT_KEY
        
    # Search for RIS Result Id's on Google Scholar
    def searchScholar(self, TERM = "", MIN_YEAR="",SAVE_BIB=False):
        """
        Search for journal articles

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

        # Set SAVE_BIB for search2Zotero
        self.SAVE_BIB = SAVE_BIB
        
        # Scrape Results, Extract Result Id's
        try:
            json_data = search.get_raw_json()
            data = json.loads(json_data)
            df = pd.json_normalize(data['organic_results'])
            ris = df['result_id']
            self.ris = ris
        except:
            "ERROR: The initial search failed because Google sucks..."
            
        return 0
    
    # Convert RIS Result Id to Bibtex Citation
    def search2Zotero(self):
        """
        Add journal articles to your Zotero library.
        """
        try:        
            ris = self.ris
        except:
            print("No results? Or an API key problem, maybe?")
            print("Fatal error!")
            ris = ""
            
        for i in ris:
            # Announce status
            print('Now processing: ' + str(i))
            
            # Get the Citation!
            params = {
              "api_key": self.API_KEY,
              "device": "desktop",
              "engine": "google_scholar_cite",
              "q": i
            }

            search = GoogleSearch(params)
            citation = search.get_dict()

            # Get APA Format Citation and Parse
            try:
                print(citation['citations'][1]['snippet'])
            except:
                continue

            # Cross-reference the Citation with Crossref to Get Bibtext
            base = 'https://api.crossref.org/works?query.'
            api_url = {'bibliographic':citation['citations'][1]['snippet']}
            url = urlencode(api_url)
            url = base+url
            response = requests.get(url)

            # Parse Bibtext from Crossref
            try:
                jsonResponse = response.json()
                jsonResponse = jsonResponse['message']
                jsonResponse = jsonResponse['items']
                jsonResponse = jsonResponse[0]
            except:
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
                fn = "my_bib_"+str(ts)+".bib"
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
            except:
                continue
            try: # test to make sure it worked
                len(bib_dict['author']) > 0
            except:
                continue
            # Connect to Zotero
            zot = zotero.Zotero(self.ZOT_ID, 'user', self.ZOT_KEY)
            template = zot.item_template('journalArticle') # Set Template
            
            # Retreive DOI numbers of existing articles to avoid duplication of citations
            items = zot.items() #
            doi_holder = []
            for idx in range(len(items)):
                try:
                    doi_holder.append(items[idx]['data']['DOI'])
                    if str(jsonResponse['DOI']) in doi_holder:
                        next
                    else:
                        pass
                except:
                    next
                    
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
                template['DOI'] = str(jsonResponse['DOI'])
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
                mydate = bib_dict['month']+' '+bib_dict['year']
                template['date'] = str(datetime.datetime.strptime(mydate, '%b %Y').date())
            except:
                try:
                    mydate = bib_dict['year']
                    template['date'] = str(bib_dict['year'])
                except:
                    continue
                            

            # Parse Names into Template/Data
            try:
                num_authors = len(bib_dict['author'])
                template['creators'] = []

                for a in bib_dict['author']:
                    split = bibtexparser.customization.splitname(a, strict_mode=False)
                    template['creators'].append({'creatorType': 'author', 'firstName': split['first'][0], 'lastName': split['last'][0]})

                print(template)

                zot.create_items([template])
            except:
                continue

        return 0