## To do: 
# 1. Make this into a proper Python library
# 2. Make a non-Zotero-specific version
# 3. Add other formats, support for middle initials / suffixes 

# Libraries
from bibtexparser.bparser import BibTexParser
from bs4 import BeautifulSoup
from collections import Counter
from datetime import date
from habanero import Crossref
from io import BytesIO
from pyzotero import zotero
from serpapi import GoogleSearch
from urllib.parse import urlencode

import arxiv
import bibtexparser
import datetime
import json
import math
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
    
    :param DOWNLOAD_DEST: Optional download directory
    :type DOWNLOAD_DEST: str
    """
 
    def __init__(self, API_KEY  = "", ZOT_ID = "", ZOT_KEY = "",DOWNLOAD_DEST = "."):
        '''
        Instantiate a serpZot object for API management        
        '''
        print("Reminder: Make sure your Zotero key has write permissions.")
        self.API_KEY       = API_KEY
        self.ZOT_ID        = ZOT_ID
        self.ZOT_KEY       = ZOT_KEY
        self.DOWNLOAD_DEST = DOWNLOAD_DEST

    @staticmethod
    def get_cosine(vec1, vec2):
        '''
        Helper function that takes 2 vectors from text_to_vector
        
        :param vec1: vector from text_to_vector
        :type vec1: ve
        :param vec2: vector from text_to_vector
        '''
        intersection = set(vec1.keys()) & set(vec2.keys())
        numerator = sum([vec1[x] * vec2[x] for x in intersection])

        sum1 = sum([vec1[x] ** 2 for x in list(vec1.keys())])
        sum2 = sum([vec2[x] ** 2 for x in list(vec2.keys())])
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        if not denominator:
            return 0.0
        else:
            return float(numerator) / denominator

    @staticmethod
    def text_to_vector(text):
        '''
        Converts strings to vectors
        
        :param text: search term (title, etc)
        :type text: str
        '''
        # Credit: https://stackoverflow.com/questions/15173225/calculate-cosine-similarity-given-2-sentence-strings
        WORD = re.compile(r"\w+")
        words = WORD.findall(text)
        return Counter(words)       

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
            base     = 'https://api.crossref.org/works?query.'
            api_url  = {'bibliographic':citation['citations'][1]['snippet']}
            url      = urlencode(api_url)
            url      = base+url
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

    def cleanZot(ZOT_ID = "", ZOT_KEY = "",SEARCH_TERM=""):
        # Connect to Zotero
        zot = zotero.Zotero(ZOT_ID, 'user', ZOT_KEY)

        zot.add_parameters(q=SEARCH_TERM)
        items = zot.everything(zot.items())

        message = "Number of items retreived from your library:" + str(len(items))
        print(message)

        n=0
        for item in items:
            n = n+1
            message2 = "Processing number: " + str(n)
            print(message2)
            
            # Clean LaTex and similar garbage
            item['data']['title'] = item['data']['title'].replace("{","")
            item['data']['title'] = item['data']['title'].replace("}","")
            item['data']['title'] = item['data']['title'].replace("$\less","")
            item['data']['title'] = item['data']['title'].replace("$scp","")
            item['data']['title'] = item['data']['title'].replace("$\greater","")
            item['data']['title'] = item['data']['title'].replace("/scp","")
            item['data']['title'] = item['data']['title'].replace("$$","")
            item['data']['title'] = item['data']['title'].replace("$","")
            item['data']['title'] = item['data']['title'].replace("\\upkappa","k")
            item['data']['title'] = item['data']['title'].replace("\\upalpha","α")
            item['data']['title'] = item['data']['title'].replace("\\textdollar","$") # must come after replacement of $
            item['data']['title'] = item['data']['title'].replace("\\mathplus","+")
            item['data']['title'] = item['data']['title'].replace('\\textquotedblleft','"')
            item['data']['title'] = item['data']['title'].replace('\\textquotedblright','"')
            item['data']['title'] = item['data']['title'].replace("\\textendash","-")
            item['data']['title'] = item['data']['title'].replace("$\textbackslashsqrt","")
            item['data']['title'] = item['data']['title'].replace("\\textbackslashsqrt","")
            item['data']['title'] = item['data']['title'].replace("\\textbackslash","")
            item['data']['title'] = item['data']['title'].replace("\textemdash","-")
            item['data']['title'] = item['data']['title'].replace("\\lbraces","")
            item['data']['title'] = item['data']['title'].replace("\\lbrace=","")
            item['data']['title'] = item['data']['title'].replace("\\rbrace=","")
            item['data']['title'] = item['data']['title'].replace("\\rbrace","")
            item['data']['title'] = item['data']['title'].replace("\\rbrace","")
            item['data']['title'] = item['data']['title'].replace("$\sim$","~")
            item['data']['title'] = item['data']['title'].replace("$\\sim$","~")
            item['data']['title'] = item['data']['title'].replace("\\&amp","&")
            item['data']['title'] = item['data']['title'].replace("\&amp","&")
            item['data']['title'] = item['data']['title'].replace("\\mathsemicolon",";")
            item['data']['title'] = item['data']['title'].replace("\\mathcolon",":")
            item['data']['title'] = item['data']['title'].replace("\mathsemicolon",";")
            item['data']['title'] = item['data']['title'].replace("\mathcolon",":")
            item['data']['title'] = item['data']['title'].replace("\\#",":")

        # Update the cloud with the improvements
        print("Updating your cloud library...")
        zot.update_items(items)

        print("Done! I hope this made things more readable.")
        # Return 0
        return 0

    def arxivDownload(self, ZOT_ID = "", ZOT_KEY = "",SEARCH_TERM="",GET_SOURCE=False,DOWNLOAD_DEST="."):
        '''
        :param ZOT_ID: Zotero user (aka library) Id
        :type ZOT_ID: str

        :param ZOT_KEY: Zotero API key
        :type ZOT_KEY: str

        :param SEARCH_TERM: Search your library with this term to select papers for downloading.
        : type SEARCH_TERM: str

        :param GET_SOURCE: If True then attempt to download .tar.gz source files of a paper or papers.
        : type GET_SOURCE: bool
        '''
        ZOT_ID        = self.ZOT_ID
        ZOT_KEY       = self.ZOT_KEY
        DOWNLOAD_DEST = self.DOWNLOAD_DEST
        # Connect to Zotero
        zot = zotero.Zotero(ZOT_ID, 'user', ZOT_KEY)

        zot.add_parameters(q=SEARCH_TERM)
        items = zot.everything(zot.items())

        message = "Number of items retreived from your library:" + str(len(items))
        print(message)

        n=0
        for item in items:
            # Announce status
            n = n+1
            message2 = "Processing number: " + str(n)
            print(message2)
            #print(item['data']['title'])
            if item['data']['itemType'] == 'journalArticle':
                text1 = item['data']['title']
                string = re.sub('[ ](?=[ ])|[^-_,A-Za-z0-9 ]+','',text1)
                vector1 = self.text_to_vector(string)

                search = arxiv.Search(
                  query = 'ti:'+"'"+string+"'",
                  max_results = 10,
                  sort_by = arxiv.SortCriterion.Relevance
                )
                #cosine_holder = []
                for result in search.results():
                    vector2 = self.text_to_vector(result.title)
                    cosine = self.get_cosine(vector1, vector2)
                    #cosine_holder.append({result.title:cosine})
                    if cosine > .9:
                        #result.doi
                        print("Match found!: ")
                        print(text1)
                        print(result.entry_id)
                        result.download_pdf(dirpath=DOWNLOAD_DEST)
                        files = [os.path.join(DOWNLOAD_DEST, x) for x in os.listdir(DOWNLOAD_DEST) if x.endswith(".pdf")]
                        newest = max(files , key = os.path.getctime)
                        zot.attachment_simple([newest],item['key'])
        return 0
    
    def cleanZot(self, ZOT_ID = "", ZOT_KEY = "",SEARCH_TERM=""):
        # Get keys / id from Self
        ZOT_ID        = self.ZOT_ID
        ZOT_KEY       = self.ZOT_KEY
        
        # Connect to Zotero
        zot = zotero.Zotero(ZOT_ID, 'user', ZOT_KEY)

        zot.add_parameters(q=SEARCH_TERM)
        items = zot.everything(zot.items())

        message = "Number of items retreived from your library:" + str(len(items))
        print(message)

        n=0
        for item in items:
            n = n+1
            message2 = "Processing number: " + str(n)
            # Clean LaTex and similar garbage
            item['data']['title'] = item['data']['title'].replace("{","")
            item['data']['title'] = item['data']['title'].replace("}","")
            item['data']['title'] = item['data']['title'].replace("$\less","")
            item['data']['title'] = item['data']['title'].replace("$scp","")
            item['data']['title'] = item['data']['title'].replace("$\greater","")
            item['data']['title'] = item['data']['title'].replace("/scp","")
            item['data']['title'] = item['data']['title'].replace("$$","")
            item['data']['title'] = item['data']['title'].replace("$","")
            item['data']['title'] = item['data']['title'].replace("\\upkappa","k")
            item['data']['title'] = item['data']['title'].replace("\\upalpha","α")
            item['data']['title'] = item['data']['title'].replace("\\textdollar","$") # must come after replacement of $
            item['data']['title'] = item['data']['title'].replace("\\mathplus","+")
            item['data']['title'] = item['data']['title'].replace('\\textquotedblleft','"')
            item['data']['title'] = item['data']['title'].replace('\\textquotedblright','"')
            item['data']['title'] = item['data']['title'].replace("\\textendash","-")
            item['data']['title'] = item['data']['title'].replace("$\textbackslashsqrt","")
            item['data']['title'] = item['data']['title'].replace("\\textbackslashsqrt","")
            item['data']['title'] = item['data']['title'].replace("\\textbackslash","")
            item['data']['title'] = item['data']['title'].replace("\textemdash","-")
            item['data']['title'] = item['data']['title'].replace("\\lbraces","")
            item['data']['title'] = item['data']['title'].replace("\\lbrace=","")
            item['data']['title'] = item['data']['title'].replace("\\rbrace=","")
            item['data']['title'] = item['data']['title'].replace("\\rbrace","")
            item['data']['title'] = item['data']['title'].replace("\\rbrace","")
            item['data']['title'] = item['data']['title'].replace("$\sim$","~")
            item['data']['title'] = item['data']['title'].replace("$\\sim$","~")
            item['data']['title'] = item['data']['title'].replace("\\&amp","&")
            item['data']['title'] = item['data']['title'].replace("\&amp","&")
            item['data']['title'] = item['data']['title'].replace("\\mathsemicolon",";")
            item['data']['title'] = item['data']['title'].replace("\\mathcolon",":")
            item['data']['title'] = item['data']['title'].replace("\mathsemicolon",";")
            item['data']['title'] = item['data']['title'].replace("\mathcolon",":")
            item['data']['title'] = item['data']['title'].replace("\\#",":")

        # Update the cloud with the improvements
        print("Updating your cloud library...")
        zot.update_items(items)

        print("Done! I hope this made things more readable.")
        # Return 0
        return 0