# Libraries
from bibtexparser.bparser import BibTexParser
from datetime import date, datetime
from helpers import get_cosine, text_to_vector
from pyzotero import zotero
from serpapi import GoogleSearch
from urllib.parse import urlencode

import arxiv
import bibtexparser
import json
import os
import pandas as pd
import re
import requests


class serpZot:
    """
    :param api_key: serpAPI API key
    :type api_key: str

    :param zot_id: Zotero user (aka library) Id
    :type zot_id: str

    :param zot_key: Zotero API key
    :type zot_key: str

    :param download_dest: Optional download directory
    :type download_dest: str
    """

    def __init__(self, api_key="", zot_id="", zot_key="", download_dest="."):
        """
        Instantiate a serpZot object for API management
        """
        self.df = None
        self.API_KEY = api_key
        self.DOWNLOAD_DEST = download_dest
        self.FIELD = "title"
        self.ZOT_ID = zot_id
        self.ZOT_KEY = zot_key
        self.DOI_HOLDER = set()
        print("Friendly reminder: Make sure your Zotero key has write permissions. I'm not saying it doesn't - just remdinding you because I can't check it for you.")

    # Search for RIS Result Id's on Google Scholar
    def searchScholar(self, term="", min_year="", save_bib=False):
        """
        Search for journal articles

        :param term: search term for Google Scholar
        :type term: str

        :param min_year: oldest year to search on
        :type min_year: str
        """

        # Search Parameters
        params = {
            "api_key": self.API_KEY,
            "device": "desktop",
            "engine": "google_scholar",
            "q": term,
            "hl": "en",
            "num": "20",
            "as_ylo": min_year
        }

        # Search
        search = GoogleSearch(params)

        # Set SAVE_BIB for search2Zotero
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
            print(f"An error occurred: {str(e)}")

        return 0

    # Convert RIS Result Id to Bibtex Citation
    def search2Zotero(self, FIELD="title"):
        """
        Add journal articles to your Zotero library.
        """
        df = pd.DataFrame()

        try:
            df = self.df
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print("Missing a search result dataframe.")

        # Connect to Zotero
        zot = zotero.Zotero(self.ZOT_ID, 'user', self.ZOT_KEY)
        template = zot.item_template('journalArticle')  # Set Template

        # Retreive DOI numbers of existing articles to avoid duplication of citations
        items = zot.items()
        if not self.DOI_HOLDER:  # Populate it only if it's empty
            for item in items:
                try:
                    self.DOI_HOLDER.add(item['data']['DOI'])
                except KeyError:
                    continue  # Skip items without a DOI

        try:
            ris = self.ris
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print("No results? Or an API key problem, maybe?")
            print("Fatal error!")
            ris = ""

        for i in ris:
            # Announce status
            print(f'Now processing: {i}')

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
                citation_text = citation['citations'][1]['snippet']
                doi_pattern = re.compile(r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b', re.IGNORECASE)
                doi_match = doi_pattern.search(citation_text)
                if doi_match:
                    new_doi = doi_match.group()
                else:
                    print("DOI not found in citation snippet.")
                    continue  # Skip to next iteration if DOI not found

                if new_doi in self.DOI_HOLDER:
                    print(f"DOI {new_doi} already exists in Zotero. Skipping.")
                    continue  # Skip this item since it's already in the library
                else:
                    self.DOI_HOLDER.add(new_doi)
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                continue

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
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                continue
            try:  # test to make sure it worked
                len(bib_dict['author']) > 0
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                continue

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
            try:
                template[self.FIELD] = bib_dict[self.FIELD]
            except:
                pass

            # Fix Date
            try:
                mydate = bib_dict['month'] + ' ' + bib_dict['year']
                template['date'] = str(datetime.strptime(mydate, '%b %Y').date())
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
                    template['creators'].append(
                        {'creatorType': 'author', 'firstName': split['first'][0], 'lastName': split['last'][0]})

                print(template)

                zot.create_items([template])

            except Exception as e:
                print(f"An error occurred: {e}")
                continue

        return 0

    def cleanZot(self, SEARCH_TERM="", FIELD="title"):
        # Get keys / id from Self
        # Ignore any errors about it not being used
        id = self.ZOT_ID
        key = self.ZOT_KEY

        # Connect to Zotero
        zot = zotero.Zotero(id, 'user', key)

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
                item['data'][FIELD] = item['data'][FIELD].replace("{", "")
                item['data'][FIELD] = item['data'][FIELD].replace("}", "")
                item['data'][FIELD] = item['data'][FIELD].replace("$\less", "")
                item['data'][FIELD] = item['data'][FIELD].replace("$scp", "")
                item['data'][FIELD] = item['data'][FIELD].replace("$\greater", "")
                item['data'][FIELD] = item['data'][FIELD].replace("/scp", "")
                item['data'][FIELD] = item['data'][FIELD].replace("$$", "")
                item['data'][FIELD] = item['data'][FIELD].replace("$", "")
                item['data'][FIELD] = item['data'][FIELD].replace("\\upkappa", "k")
                item['data'][FIELD] = item['data'][FIELD].replace("\\upalpha", "α")
                item['data'][FIELD] = item['data'][FIELD].replace("\\textdollar",
                                                                  "$")  # must come after replacement of $
                item['data'][FIELD] = item['data'][FIELD].replace("\\mathplus", "+")
                item['data'][FIELD] = item['data'][FIELD].replace('\\textquotedblleft', '"')
                item['data'][FIELD] = item['data'][FIELD].replace('\\textquotedblright', '"')
                item['data'][FIELD] = item['data'][FIELD].replace('{\\textquotesingle}', "'")
                item['data'][FIELD] = item['data'][FIELD].replace('{\\\textquotesingle}', "'")
                item['data'][FIELD] = item['data'][FIELD].replace('{\\\\textquotesingle}', "'")
                item['data'][FIELD] = item['data'][FIELD].replace("\\textendash", "-")
                item['data'][FIELD] = item['data'][FIELD].replace("$\textbackslashsqrt", "")
                item['data'][FIELD] = item['data'][FIELD].replace("\\textbackslashsqrt", "")
                item['data'][FIELD] = item['data'][FIELD].replace("\\textbackslash", "")
                item['data'][FIELD] = item['data'][FIELD].replace("\textemdash", "-")
                item['data'][FIELD] = item['data'][FIELD].replace("\\lbraces", "")
                item['data'][FIELD] = item['data'][FIELD].replace("\\lbrace=", "")
                item['data'][FIELD] = item['data'][FIELD].replace("\\rbrace=", "")
                item['data'][FIELD] = item['data'][FIELD].replace("\\rbrace", "")
                item['data'][FIELD] = item['data'][FIELD].replace("\\rbrace", "")
                item['data'][FIELD] = item['data'][FIELD].replace("$\sim$", "~")
                item['data'][FIELD] = item['data'][FIELD].replace("$\\sim$", "~")
                item['data'][FIELD] = item['data'][FIELD].replace("\\&amp", "&")
                item['data'][FIELD] = item['data'][FIELD].replace("\&amp", "&")
                item['data'][FIELD] = item['data'][FIELD].replace("\\mathsemicolon", ";")
                item['data'][FIELD] = item['data'][FIELD].replace("\\mathcolon", ":")
                item['data'][FIELD] = item['data'][FIELD].replace("\mathsemicolon", ";")
                item['data'][FIELD] = item['data'][FIELD].replace("\mathcolon", ":")
                item['data'][FIELD] = item['data'][FIELD].replace("\\#", ":")
                item['data'][FIELD] = item['data'][FIELD].replace("\\textregistered", "®")
                item['data'][FIELD] = item['data'][FIELD].replace("\textregistered", "®")
                item['data'][FIELD] = item['data'][FIELD].replace("\\\textregistered", "®")
                item['data'][FIELD] = item['data'][FIELD].replace("#1I/`", "'")
                item['data'][FIELD] = item['data'][FIELD].replace("1I/", "'")
                item['data'][FIELD] = item['data'][FIELD].replace("\1I/", "'")  # {\’{\i}}   {\’{\a}}   {\’{o}}
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{\a}}", "a")
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{\e}}", "e")
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{\i}}", "i")
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{\o}}", "o")
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{a}}", "a")
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{e}}", "e")
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{i}}", "i")
                item['data'][FIELD] = item['data'][FIELD].replace("{\’{o}}", "o")
            except:
                pass

        # Update the cloud with the improvements
        print("Updating your cloud library...")
        zot.update_items(items)

        print("Done! I hope this made things more readable.")
        # Return 0
        return 0

    def downloadResponse(self, response, path):
        if response.headers['content-type'] == "application/pdf":
            with open(path, "wb") as f:
                f.write(response.content)
                f.close()
            return 1
        elif re.findall("application/pdf", response.text):
            pdf_link = "https:" + \
                       re.findall('src=".*\.pdf.*"', response.text)[0].split('"')[1].split('#')[0]
            pdf_response = requests.get(pdf_link)
            if pdf_response.headers['content-type'] == "application/pdf":
                with open(path, "wb") as pf:
                    pf.write(pdf_response.content)
                    pf.close()
                return 1
        return 0

    def sciHubDownload(self, DOWNLOAD_DEST, DOI):
        sci_hub_url = "https://sci-hub.se/"
        sci_hub_url += DOI

        response = requests.get(sci_hub_url)

        name = DOI.replace("/", "_") + ".pdf"
        path = os.path.join(DOWNLOAD_DEST, name)
        return self.downloadResponse(response, path)

    def medarixDownload(self, DOWNLOAD_DEST, DOI):

        medUrl = "https://www.medrxiv.org/"
        # The url looks like https://www.medrxiv.org/content/10.1101/2024.02.03.24302058v1.full.pdf
        medUrl += "content/"
        medUrl += DOI + ".pdf"

        response = requests.get(medUrl)
        name = DOI.replace("/", "_") + ".pdf"
        path = os.path.join(DOWNLOAD_DEST, name)

        return self.downloadResponse(response, path)

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
        ZOT_ID = self.ZOT_ID
        ZOT_KEY = self.ZOT_KEY
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
                    vector1 = text_to_vector(string)

                    search = arxiv.Search(
                        query='ti:' + "'" + string + "'",
                        max_results=10,
                        sort_by=arxiv.SortCriterion.Relevance
                    )
                    DOI = item['data'].get('DOI')
                    pdf_downloaded = 0
                    for result in search.results():
                        vector2 = text_to_vector(result.title)
                        cosine = get_cosine(vector1, vector2)
                        # cosine_holder.append({result.title:cosine})
                        if cosine > .8:
                            # result.doi
                            pdf_downloaded += 1
                            print("Match found!: ")
                            print(text1)
                            print(result.entry_id)
                            result.download_pdf(dirpath=DOWNLOAD_DEST)

                    numDownloads = 0
                    if pdf_downloaded == 0:
                        print("Attempting download from SCI-HUB")
                        numDownloads = self.sciHubDownload(DOWNLOAD_DEST, DOI=DOI)

                    if numDownloads == 0:
                        # call the media one
                        print("Attempting download from medarxiv")
                        numDownloads = self.medarixDownload(DOWNLOAD_DEST, DOI=DOI)

                    files = [os.path.join(DOWNLOAD_DEST, x) for x in os.listdir(DOWNLOAD_DEST) if x.endswith(".pdf")]
                    print(files)
                    newest = max(files, key=os.path.getctime)
                    zot.attachment_simple([newest], item['key'])
                    break

            except Exception as e:
                print(e)
                pass
        return 0
