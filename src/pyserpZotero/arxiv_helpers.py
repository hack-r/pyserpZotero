# arxiv_helpers.py

from helpers import get_cosine, text_to_vector
from pyzotero import zotero

import arxiv
import os
import re
import requests


def downloadResponse(response, path):
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

    message = "Number of items retrieved from your library:" + str(len(items))
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
