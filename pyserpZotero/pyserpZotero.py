## To do:
# 1. Make this into a proper Python library
# 2. Make a non-Zotero-specific version
# 3. Add other formats, support for middle initials / suffixes

import datetime
import json
import math
import os
import re
import subprocess
from collections import Counter
from datetime import date
from io import BytesIO
from pathlib import Path
from tabnanny import verbose
from urllib.parse import urlencode

import arxiv
import bibtexparser
import numpy as np
import pandas as pd
import requests

# Libraries
from bibtexparser.bparser import BibTexParser
from bs4 import BeautifulSoup
from habanero import Crossref
from pyzotero import zotero
from serpapi import GoogleScholarSearch, GoogleSearch


def clean_mml(mml_input: str):
    """
    _summary_

    :param mml_input: _description_
    :type mml_input: str
    """
    # copy the input
    result = mml_input
    result = result.replace(r"$\less$", "<")
    result = result.replace(r"$\greater$", ">")
    result = re.sub(r"<(.*?>)(.*)</\1", "", result)
    result = re.sub(r"<mml:math (.*)>(.*)</mml:math>", "", result)

    # Convert multiline string to single line
    result_as_list = [line.strip() for line in result.splitlines()]
    print(result_as_list)
    # join results and if not first item wrap in ()
    new_result = ""
    for i, entry in enumerate(result_as_list):
        if len(entry) == 1:
            return entry[0]
        elif entry == "":
            continue

        else:
            if i == 0:
                new_result += entry
            else:
                new_result += "(" + entry + ")"
    result = new_result

    print(result)

    return result


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

    def __init__(self, API_KEY="", ZOT_ID="", ZOT_KEY="", DOWNLOAD_DEST="."):
        """
        Instantiate a serpZot object for API management
        """
        print("Reminder: Make sure your Zotero key has write permissions.")
        self.API_KEY = API_KEY
        self.ZOT_ID = ZOT_ID
        self.ZOT_KEY = ZOT_KEY
        self.DOWNLOAD_DEST = DOWNLOAD_DEST
        # self.clear_auto_bib()
        self._search_scholar_done = False

    @staticmethod
    def get_cosine(vec1, vec2):
        """
        Helper function that takes 2 vectors from text_to_vector

        :param vec1: vector from text_to_vector
        :type vec1: ve
        :param vec2: vector from text_to_vector
        """
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
        """
        Converts strings to vectors

        :param text: search term (title, etc)
        :type text: str
        """
        # Credit: https://stackoverflow.com/questions/15173225/calculate-cosine-similarity-given-2-sentence-strings
        WORD = re.compile(r"\w+")
        words = WORD.findall(text)
        return Counter(words)

    def clear_auto_bib(self):
        """
        Clear the auto_cite file
        """
        with open("auto_cite.bib", "w") as f:
            f.write("")
        return self

    # Search for RIS Result Id's on Google Scholar
    def searchScholar(self, TERM="", MIN_YEAR="", SAVE_BIB=False):
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
            "num": "3",
            "as_ylo": MIN_YEAR,
        }

        # Search
        search = GoogleSearch(params)

        # Set SAVE_BIB for search2Zotero
        self.SAVE_BIB = SAVE_BIB

        # Scrape Results, Extract Result Id's
        try:
            results = search.get_dict()
            json.dump(results, open("results.json", "w"), indent=4)
            print(f"Search results saved to results.json.")

            ris = results["organic_results"]["result_id"]
            self.ris = ris
        except:
            "ERROR: The initial search failed because Google sucks..."

        return self

    # Convert RIS Result Id to Bibtex Citation
    def convert_ris_to_bib(self, use_saved_ris=False, saved_ris_file: str = ""):
        """
        Convert RIS to BibTeX

        :raises ValueError: _description_
        :return: _description_
        :rtype: _type_
        """
        if not self._search_scholar_done and not use_saved_ris:
            raise ValueError("You must run searchScholar() before search2Zotero() or use use_saved_ris=True")

        if not self._search_scholar_done and use_saved_ris:
            with open(saved_ris_file) as f:
                ris = f.readlines()
            self.ris = ris

        ris = self.ris

        for i, ind_ris in enumerate(ris):
            # Announce status
            print("Now processing: " + str(ind_ris))

            # Get the Citation!
            params = {"api_key": self.API_KEY, "device": "desktop", "engine": "google_scholar_cite", "q": i}

            search = GoogleSearch(params)
            citation = search.get_dict()

            ## google search don't print to console
            # print(citation)

            self.citation = citation

            print(citation)

            # Get APA Format Citation and Parse
            try:
                print(citation["citations"][0]["snippet"])
            except:
                continue

            # Cross-reference the Citation with Crossref to Get Bibtext
            base = "https://api.crossref.org/works?query."
            api_url = {"bibliographic": citation["citations"][0]["snippet"]}
            url = urlencode(api_url)
            url = base + url
            response = requests.get(url)

            # Parse Bibtext from Crossref

            try:
                jsonResponse = response.json()
                jsonResponse = jsonResponse["message"]
                jsonResponse = jsonResponse["items"]
                jsonResponse = jsonResponse[0]
            except:
                continue
            curl_str = 'curl -LH "Accept: application/x-bibtex" http://dx.doi.org/' + jsonResponse["DOI"]
            # run curl command with no output
            #! This line controls output that i suppressed
            result = subprocess.check_output(curl_str, shell=True).decode("utf-8")

            # Write bibtext file
            with open("auto_cite.bib", "a") as text_file:
                text_file.write("\n")
                text_file.write(result)

            # Parse bibtext
            with open("auto_cite.bib") as bibtex_file:
                parser = BibTexParser()
                parser.customization = bibtexparser.customization.author
                bib_database = bibtexparser.load(bibtex_file, parser=parser)
            try:
                self.bib_dict = bib_database.entries[0]
            except:
                continue
            try:  # test to make sure it worked
                len(self.bib_dict["author"]) > 0
            except:
                continue

            # parse bibtext to readable format
            bib_dict = self.bib_dict
            bib_dict["author"] = bib_dict["author"][0]
            bib_dict["author"] = bib_dict["author"].replace(" and ", ", ")
            bib_dict["author"] = bib_dict["author"].replace(" ", ", ")
            bib_dict["author"] = bib_dict["author"].replace(",,", ",")
            bib_dict["author"] = bib_dict["author"].replace(",,", ",")

            self.bib_dict = bib_dict

            return self

        def search2Zotero(self):
            """
            Search for journal articles
            """

            # Connect to Zotero
            zot = zotero.Zotero(self.ZOT_ID, "user", self.ZOT_KEY)
            template = zot.item_template("journalArticle")  # Set Template
            print(template)

            # Retreive DOI numbers of existing articles to avoid duplication of citations
            items = zot.items()  #
            doi_holder = []
            for idx in range(len(items)):
                try:
                    doi_holder.append(items[idx]["data"]["DOI"])
                    if str(jsonResponse["DOI"]) in doi_holder:
                        next
                    else:
                        pass
                except:
                    next

                # Populate Zotero Template with Data
                try:
                    template["publicationTitle"] = bib_dict["journal"]
                except:
                    pass
                try:
                    template[FIELD] = bib_dict[FIELD]
                except:
                    pass
                try:
                    template["DOI"] = str(jsonResponse["DOI"])
                except:
                    pass
                try:
                    template["accessDate"] = str(date.today())
                except:
                    pass
                try:
                    template["extra"] = str(bib_database.comments)
                except:
                    pass
                try:
                    template["url"] = bib_dict["url"]
                except:
                    pass
                try:
                    template["volume"] = bib_dict["volume"]
                except:
                    pass
                try:
                    template["issue"] = bib_dict["number"]
                except:
                    pass
                try:
                    template["abstractNote"] = df["snippet"][0]
                except:
                    pass

                # Fix Date
                try:
                    mydate = bib_dict["month"] + " " + bib_dict["year"]
                    template["date"] = str(datetime.datetime.strptime(mydate, "%b %Y").date())
                except:
                    try:
                        mydate = bib_dict["year"]
                        template["date"] = str(bib_dict["year"])
                    except:
                        continue

                # Parse Names into Template/Data
                try:
                    num_authors = len(bib_dict["author"])
                    template["creators"] = []

                    for a in bib_dict["author"]:
                        split = bibtexparser.customization.splitname(a, strict_mode=False)
                        template["creators"].append(
                            {"creatorType": "author", "firstName": split["first"][0], "lastName": split["last"][0]}
                        )

                    print(template)
                    zot.create_items([template])
                except:
                    continue

                return 0

    def cleanZot(self, ZOT_ID="", ZOT_KEY="", SEARCH_TERM="", FIELD="title"):
        # Get keys / id from Self
        ZOT_ID = self.ZOT_ID
        ZOT_KEY = self.ZOT_KEY

        # Connect to Zotero
        zot = zotero.Zotero(ZOT_ID, "user", ZOT_KEY)

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
                print(item["data"][FIELD])
                item["data"][FIELD] = clean_mml(item["data"][FIELD])
                print(item["data"][FIELD])

            except:
                pass

        # Update the cloud with the improvements
        print("Updating your cloud library...")
        zot.update_items(items)

        print("Done! I hope this made things more readable.")
        # Return 0
        return 0

    def arxivDownload(self, ZOT_ID="", ZOT_KEY="", SEARCH_TERM="", GET_SOURCE=False, DOWNLOAD_DEST="."):
        """
        :param ZOT_ID: Zotero user (aka library) Id
        :type ZOT_ID: str

        :param ZOT_KEY: Zotero API key
        :type ZOT_KEY: str

        :param SEARCH_TERM: Search your library with this term to select papers for downloading.
        : type SEARCH_TERM: str

        :param GET_SOURCE: If True then attempt to download .tar.gz source files of a paper or papers.
        : type GET_SOURCE: bool
        """
        ZOT_ID = self.ZOT_ID
        ZOT_KEY = self.ZOT_KEY
        DOWNLOAD_DEST = self.DOWNLOAD_DEST
        # Connect to Zotero
        zot = zotero.Zotero(ZOT_ID, "user", ZOT_KEY)

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
                if item["data"]["itemType"] == "journalArticle":
                    text1 = item["data"][FIELD]
                    string = re.sub("[ ](?=[ ])|[^-_,A-Za-z0-9 ]+", "", text1)
                    vector1 = self.text_to_vector(string)

                    search = arxiv.Search(
                        query="ti:" + "'" + string + "'", max_results=10, sort_by=arxiv.SortCriterion.Relevance
                    )
                    # cosine_holder = []
                    for result in search.results():
                        vector2 = self.text_to_vector(result.title)
                        cosine = self.get_cosine(vector1, vector2)
                        # cosine_holder.append({result.title:cosine})
                        if cosine > 0.9:
                            # result.doi
                            print("Match found!: ")
                            print(text1)
                            print(result.entry_id)
                            result.download_pdf(dirpath=DOWNLOAD_DEST)
                            files = [
                                os.path.join(DOWNLOAD_DEST, x) for x in os.listdir(DOWNLOAD_DEST) if x.endswith(".pdf")
                            ]
                            newest = max(files, key=os.path.getctime)
                            zot.attachment_simple([newest], item["key"])
            except:
                pass
        return 0
