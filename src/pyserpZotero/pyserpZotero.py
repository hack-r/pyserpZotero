## To do:
# 1. Add other formats, support for middle initials / suffixes

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
import pdb

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
            except:
                continue
            try:  # test to make sure it worked
                len(bib_dict['author']) > 0
            except:
                continue
            # Connect to Zotero
            zot = zotero.Zotero(self.ZOT_ID, 'user', self.ZOT_KEY)
            template = zot.item_template('journalArticle')  # Set Template

            # Retreive DOI numbers of existing articles to avoid duplication of citations
            items = zot.items()  #
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
                template[FIELD] = bib_dict[FIELD]
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
                mydate = bib_dict['month'] + ' ' + bib_dict['year']
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

    def cleanZot(self, ZOT_ID="", ZOT_KEY="", SEARCH_TERM="", FIELD="title"):
        # Get keys / id from Self
        ZOT_ID        = self.ZOT_ID
        ZOT_KEY       = self.ZOT_KEY

        # Connect to Zotero
        zot = zotero.Zotero(ZOT_ID, 'user', ZOT_KEY)

        zot.add_parameters(q=SEARCH_TERM)
        items = zot.everything(zot.items())

        message = "Number of items retreived from your library:" + str(len(items))
        print(message)

        n = 0
        for item in items:
            n = n + 1
            message2 = "Processing number: " + str(n)
            try:
                # Clean LaTex and similar garbage
                item['data'][FIELD] = item['data'][FIELD].replace("{","")
                item['data'][FIELD] = item['data'][FIELD].replace("}","")
                item['data'][FIELD] = item['data'][FIELD].replace("$\less","")
                item['data'][FIELD] = item['data'][FIELD].replace("$scp","")
                item['data'][FIELD] = item['data'][FIELD].replace("$\greater","")
                item['data'][FIELD] = item['data'][FIELD].replace("/scp","")
                item['data'][FIELD] = item['data'][FIELD].replace("$$","")
                item['data'][FIELD] = item['data'][FIELD].replace("$","")
                item['data'][FIELD] = item['data'][FIELD].replace("\\upkappa","k")
                item['data'][FIELD] = item['data'][FIELD].replace("\\upalpha","α")
                item['data'][FIELD] = item['data'][FIELD].replace("\\textdollar","$") # must come after replacement of $
                item['data'][FIELD] = item['data'][FIELD].replace("\\mathplus","+")
                item['data'][FIELD] = item['data'][FIELD].replace('\\textquotedblleft','"')
                item['data'][FIELD] = item['data'][FIELD].replace('\\textquotedblright','"')
                item['data'][FIELD] = item['data'][FIELD].replace('{\\textquotesingle}',"'")
                item['data'][FIELD] = item['data'][FIELD].replace('{\\\textquotesingle}',"'")
                item['data'][FIELD] = item['data'][FIELD].replace('{\\\\textquotesingle}',"'")
                item['data'][FIELD] = item['data'][FIELD].replace("\\textendash","-")
                item['data'][FIELD] = item['data'][FIELD].replace("$\textbackslashsqrt","")
                item['data'][FIELD] = item['data'][FIELD].replace("\\textbackslashsqrt","")
                item['data'][FIELD] = item['data'][FIELD].replace("\\textbackslash","")
                item['data'][FIELD] = item['data'][FIELD].replace("\textemdash","-")
                item['data'][FIELD] = item['data'][FIELD].replace("\\lbraces","")
                item['data'][FIELD] = item['data'][FIELD].replace("\\lbrace=","")
                item['data'][FIELD] = item['data'][FIELD].replace("\\rbrace=","")
                item['data'][FIELD] = item['data'][FIELD].replace("\\rbrace","")
                item['data'][FIELD] = item['data'][FIELD].replace("\\rbrace","")
                item['data'][FIELD] = item['data'][FIELD].replace("$\sim$","~")
                item['data'][FIELD] = item['data'][FIELD].replace("$\\sim$","~")
                item['data'][FIELD] = item['data'][FIELD].replace("\\&amp","&")
                item['data'][FIELD] = item['data'][FIELD].replace("\&amp","&")
                item['data'][FIELD] = item['data'][FIELD].replace("\\mathsemicolon",";")
                item['data'][FIELD] = item['data'][FIELD].replace("\\mathcolon",":")
                item['data'][FIELD] = item['data'][FIELD].replace("\mathsemicolon",";")
                item['data'][FIELD] = item['data'][FIELD].replace("\mathcolon",":")
                item['data'][FIELD] = item['data'][FIELD].replace("\\#",":")
                item['data'][FIELD] = item['data'][FIELD].replace("\\textregistered","®")
                item['data'][FIELD] = item['data'][FIELD].replace("\textregistered","®")
                item['data'][FIELD] = item['data'][FIELD].replace("\\\textregistered","®")
                item['data'][FIELD] = item['data'][FIELD].replace("#1I/`","'") 
                item['data'][FIELD] = item['data'][FIELD].replace("1I/","'") 
                item['data'][FIELD] = item['data'][FIELD].replace("\1I/","'")  #{\’{\i}}   {\’{\a}}   {\’{o}}
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{\a}}","a") 
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{\e}}","e") 
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{\i}}","i") 
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{\o}}","o") 
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{a}}","a") 
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{e}}","e") 
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{i}}","i") 
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{o}}","o") 
            except: 
                pass

        # Update the cloud with the improvements
        print("Updating your cloud library...")
        zot.update_items(items)

        print("Done! I hope this made things more readable.")
        # Return 0
        return 0

    def sciHubDownload(self, DOWNLOAD_DEST):
        sci_hub_url = "https://sci-hub.se/"
        # DOI = item['data'].get('DOI')
        DOI = "10.1002/neu.10213534"
        sci_hub_url += DOI

        response = requests.get(sci_hub_url)

        name = DOI.replace("/", "_") + ".pdf"
        path = os.path.join(DOWNLOAD_DEST, name)
        # pdb.set_trace()

        if response.headers['content-type'] == "application/pdf":
            with open(path, "wb") as f:
                f.write(response.content)
                f.close()
        elif re.findall("application/pdf", response.text):
            pdf_link = "https:" + \
                    re.findall('src=".*\.pdf.*"', response.text)[0].split('"')[1].split('#')[0]
            # pdf_link = "https://zero.sci-hub.se/182/46a2ed6f529ae730db224547694eb48b/lee2001.pdf?download=true"
            pdf_response = requests.get(pdf_link)
            if pdf_response.headers['content-type'] == "application/pdf":
                with open(path, "wb") as pf:
                    pf.write(pdf_response.content)
                    pf.close()
                return 1
        return 0
    
    def medarixDownload( self, DOWNLOAD_DEST, DOI ):

        medUrl = "https://www.medrxiv.org/"
        # The url looks like https://www.medrxiv.org/content/10.1101/2024.02.03.24302058v1.full.pdf
        medUrl += "content/"
        DOI = "10.1101/2024.02.03.24302058"
        medUrl += DOI + ".pdf"
        
        response = requests.get(medUrl)
        pdb.set_trace() 
        name = DOI.replace("/", "_") + ".pdf"
        path = os.path.join(DOWNLOAD_DEST, name)

        if response.headers['content-type'] == "application/pdf":
            with open(path, "wb") as f:
                f.write(response.content)
                f.close()
        elif re.findall("application/pdf", response.text):
            pdf_link = "https:" + \
                    re.findall('src=".*\.pdf.*"', response.text)[0].split('"')[1].split('#')[0]
            pdf_response = requests.get(pdf_link)
            if pdf_response.headers['content-type'] == "application/pdf":
                with open(path, "wb") as pf:
                    pf.write(pdf_response.content)
                    pf.close()
                return 1
        return -1 


    def arxivDownload(self, ZOT_ID="", ZOT_KEY="", SEARCH_TERM="", GET_SOURCE=False, DOWNLOAD_DEST="."):
        FIELD = 'publicationTitle'

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

        n = 0
        for item in items:
            # Announce status
            n = n + 1
            message2 = "Processing number: " + str(n)
            print(message2)
            try:
                if item['data']['itemType'] == 'journalArticle':
                    text1 = item['data'][FIELD]
                    string = re.sub('[ ](?=[ ])|[^-_,A-Za-z0-9 ]+', '', text1)
                    vector1 = self.text_to_vector(string)

                    search = arxiv.Search(
                      query       = 'ti:'+"'"+string+"'",
                      max_results = 10,
                      sort_by     = arxiv.SortCriterion.Relevance
                    )
                    # cosine_holder = []
                    pdf_downloaded = 0
                    for result in search.results():
                        vector2 = self.text_to_vector(result.title)
                        cosine = self.get_cosine(vector1, vector2)
                        # cosine_holder.append({result.title:cosine})
                        if cosine > .9:
                            # result.doi
                            pdf_downloaded += 1
                            print("Match found!: ")
                            print(text1)
                            print(result.entry_id)
                            result.download_pdf(dirpath=DOWNLOAD_DEST)

                    if pdf_downloaded == 0:
                        print("Attempting download from SCI-HUB")
                        numDownloads = self.sciHubDownload(DOWNLOAD_DEST)

                    if numDownloads == 0:
                        # call the media one 
                        print("Attempting download from medarxiv")
                        numDownloads = self.medarixDownload(DOWNLOAD_DEST, DOI="")
                        
                    files = [os.path.join(DOWNLOAD_DEST, x) for x in os.listdir(DOWNLOAD_DEST) if x.endswith(".pdf")]
                    print(files)
                    newest = max(files, key=os.path.getctime)
                    zot.attachment_simple([newest], item['key'])
                    break

            except Exception as e:
                print(e)
                pass
        return 0
    
# Load libraries
import os
import yaml

from box import Box

with open("config.yaml", "r") as ymlfile:
    cfg = Box(yaml.safe_load(ymlfile), default_box=True, default_box_attr=None)
    
API_KEY = cfg.API_KEY
ZOT_ID  = cfg.ZOT_ID
ZOT_KEY = cfg.ZOT_KEY

# Instantiate a serpZot object for API management
citeObj = serpZot(API_KEY  = API_KEY, 
                             ZOT_ID   = ZOT_ID, 
                             ZOT_KEY  = ZOT_KEY)

# Check Arxiv for Free PDFs of Papers and Attach / Upload Them To Zotero
citeObj.arxivDownload()