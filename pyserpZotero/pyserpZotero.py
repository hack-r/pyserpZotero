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
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlencode

import arxiv
import bibtexparser
import requests

# Libraries
from bibtexparser.bparser import BibTexParser
from pyzotero import zotero
from serpapi import GoogleSearch


@contextmanager
def nullify_output(suppress_stdout=True, suppress_stderr=True):
    stdout = sys.stdout
    stderr = sys.stderr
    devnull = open(os.devnull, "w")
    try:
        if suppress_stdout:
            sys.stdout = devnull
        if suppress_stderr:
            sys.stderr = devnull
        yield
    finally:
        if suppress_stdout:
            sys.stdout = stdout
        if suppress_stderr:
            sys.stderr = stderr


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
            "num": "20",
            "as_ylo": MIN_YEAR,
        }

        # Search
        with nullify_output():
            search = GoogleSearch(params)
            results = search.get_dict()

        # Set SAVE_BIB for search2Zotero
        self.SAVE_BIB = SAVE_BIB

        # Scrape Results, Extract Result Id's
        #! Can remove try/except because GoogleSearch will raise an error if no results

        json.dump(results, open("scholar_search_results.json", "w"), indent=4)
        print(f"Search results saved to scholar_search_results.json.")

        organic_results = results["organic_results"]
        ris = [result["result_id"] for result in organic_results]
        self.ris = ris

        self._search_scholar_done = True

    # Convert RIS Result Id to Bibtex Citation
    def convert_ris_to_apa_citation(self, use_saved_ris=False, saved_ris_file: Path = Path("ris.txt")):
        """
        Convert RIS to BibTeX

        :raises ValueError: _description_
        :return: _description_
        :rtype: _type_
        """
        if not self._search_scholar_done and not use_saved_ris:
            raise ValueError("You must run searchScholar() before search2Zotero() or use use_saved_ris=True")

        if not self._search_scholar_done and use_saved_ris:
            with open(saved_ris_file, "r") as f:
                ris = f.readlines()
            self.ris = ris

        ris = self.ris

        all_google_api_citations = []
        for i, ind_ris in enumerate(ris):
            # Announce status
            print("Now processing: " + str(ind_ris))

            # Get the Citation!
            params = {
                "api_key": self.API_KEY,
                "device": "desktop",
                "engine": "google_scholar_cite",
                "q": ind_ris,
            }

            with nullify_output():
                search = GoogleSearch(params)
                citation = search.get_dict()

            all_google_api_citations.append(citation)

            self.all_citations = all_google_api_citations

        # dump all citations to json
        json.dump(
            all_google_api_citations,
            open("all_google_api_citations.json", "w"),
            indent=4,
        )
        print("All citations saved to all_google_api_citations.json")
        # # Get APA Format Citation and Parse

        all_apa_citations = []
        for citation in all_google_api_citations:
            citations_json = citation["citations"]
            for citation_json in citations_json:
                if citation_json["title"] == "APA":
                    apa_citation = citation_json["snippet"]
                    all_apa_citations.append(apa_citation)
                    break

        self.all_apa_citations = all_apa_citations

    def make_bib_from_apa_cross_ref(
        self,
        default_file_name: str = "auto_cite.bib",
        overwrite_if_exists: bool = False,
    ):
        """
        Get Crossref from APA Citation
        """
        all_crossref_results = []
        all_dx_doi_org_results = []
        all_apa_citations = self.all_apa_citations
        for i, apa_citation in enumerate(all_apa_citations):
            # Cross-reference the Citation with Crossref to Get Bibtext
            base = "https://api.crossref.org/works?query."
            api_url = {"bibliographic": apa_citation}
            url = urlencode(api_url)
            url = base + url
            with nullify_output():
                response = requests.get(url)

            all_crossref_results.append(response)

            # Parse Bibtext from Crossref

            jsonResponse = response.json()
            jsonResponse = jsonResponse["message"]
            jsonResponse = jsonResponse["items"]
            jsonResponse = jsonResponse[0]

            ## combine two components into URL and wrap in quotes
            base = "http://dx.doi.org/"
            doi = jsonResponse["DOI"]
            url = base + doi
            url = '"' + url + '"'  # wrap in quotes

            arg1 = "Accept: application/x-bibtex"
            arg2 = f"http://dx.doi.org/{doi}"
            base_curl_cmd = "curl -s -LH"

            curl_str = f"""{base_curl_cmd} "{arg1}" "{arg2}" """

            self.curl_str = curl_str

            # run curl command with no output
            #! This line controls output that i suppressed
            with nullify_output():
                result = subprocess.check_output(curl_str, shell=True).decode("utf-8")
            if i == 0:
                mode = "w"
            else:
                mode = "a"
            with open(default_file_name, mode) as f:
                f.write(result)
                print("Wrote entry to file. Loop number: " + str(i))

            all_dx_doi_org_results.append(result)

        print(f"Saved bibtext to {default_file_name}")

    def make_zot_template_from_bib(self, default_file_name: str = "auto_cite.bib"):
        """
        Make Zotero Template from Bibtext
        """
        # Parse bibtext
        with open(default_file_name, "r") as bibtex_file:
            parser = BibTexParser()
            parser.customization = bibtexparser.customization.author
            self.bib_database = bibtexparser.load(bibtex_file, parser=parser)

        MAPPINGS_FROM_BIBTEXT_TO_ZOTERO = {
            "journal": "publicationTitle",
            "title": "title",
            "doi": "DOI",
            "url": "url",
            "volume": "volume",
            "number": "issue",
            "snippet": "extra",
        }

        # apply mapping if key exists, otherwise leave blank
        entry_dict_list = []
        for entry in self.bib_database.entries:
            matched_keys = dict(
                (MAPPINGS_FROM_BIBTEXT_TO_ZOTERO[k], v)
                for k, v in entry.items()
                if MAPPINGS_FROM_BIBTEXT_TO_ZOTERO.get(k) is not None
            )
            # add itemType to dict
            matched_keys["itemType"] = "journalArticle"
            # add today as accessDate
            matched_keys["accessDate"] = datetime.date.today().strftime("%Y-%m-%d")

            entry_dict_list.append(matched_keys)

        # Connect to Zotero
        print(f"entry_dict_list: {entry_dict_list}")
        zot = zotero.Zotero(self.ZOT_ID, "user", self.ZOT_KEY)
        for zot_item in entry_dict_list:
            print(zot_item)
            zot.check_items([zot_item])
            zot.create_items([zot_item])

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
                        query="ti:" + "'" + string + "'",
                        max_results=10,
                        sort_by=arxiv.SortCriterion.Relevance,
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
