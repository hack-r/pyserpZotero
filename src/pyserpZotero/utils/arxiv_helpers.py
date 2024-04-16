# utils/arxiv_helpers.py
from .helpers import get_cosine, text_to_vector
import arxiv
import os
import re
import requests
import tempfile

# Assuming your download function looks something like this
def download_pdf(url):
    """
    Download a PDF from a given URL.

    Parameters:
    - url (str): The URL of the PDF to be downloaded.

    Returns:
    - str or None: The file path to the downloaded PDF if successful, None otherwise.
    """
    response = requests.get(url)
    if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
        # Use NamedTemporaryFile to automatically handle the file creation
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(response.content)
        temp_file.close()
        return temp_file.name
    return None


def download_response(response, path, server="se"):
    """
    Handle the response from a PDF download attempt, saving the file if successful.

    Parameters:
    - response: The response object from the download attempt.
    - path (str): The file path where the PDF should be saved.
    - server (str): Identifier for the PDF source server, default is "se" for Sci-Hub.se.

    Returns:
    - bool: True if the PDF was successfully downloaded and saved, False otherwise.
    """
    try:
        if response.headers.get('content-type') == "application/pdf":
            with open(path, "wb") as f:
                f.write(response.content)
            return True
        elif "application/pdf" in response.text:
            location = re.findall('src=".*\.pdf.*"', response.text)[0].split('"')[1].split('#')[0]
            
            # It also could be the absolute link present in sci-hub.
            pdf_link = "https:" + re.findall('src=".*\.pdf.*"', response.text)[0].split('"')[1].split('#')[0]
            
            if "sci-hub" not in location:
                if server == "se":
                    pdf_link = "https://sci-hub.se" + location
                else:
                    pdf_link = "https://sci-hub.ru" + location

            pdf_response = requests.get(pdf_link)
            if pdf_response.headers.get('content-type') == "application/pdf":
                with open(path, "wb") as pf:
                    pf.write(pdf_response.content)
                return True

    except Exception as e:
        print(f"Failed to download PDF: {e}")
        return False
    return False


def ensure_download_dest_is_valid(download_dest):
    """
    Ensure the specified download destination is valid, creating directories as needed.

    Parameters:
    - download_dest (str): The intended directory for downloading files.

    Returns:
    - str: The normalized, absolute path to the download destination.
    """
    # Check if download_dest is a valid path
    if not isinstance(download_dest, str) or not download_dest.strip():
        download_dest = "."

    # Ensure download_dest exists
    os.makedirs(download_dest, exist_ok=True)

    # Normalize the path to remove any redundant separators, etc.
    download_dest = os.path.normpath(download_dest)

    return download_dest


def scihub_download(download_dest, doi):
    """
    Attempt to download a PDF from Sci-Hub using a DOI.

    Parameters:
    - download_dest (str): The directory to save the downloaded PDF.
    - doi (str): The DOI of the document to download.

    Returns:
    - tuple: (bool, str) indicating success status and the file path to the downloaded PDF.
    """
    try:
        sci_hub_url = "https://sci-hub.se/" + doi
        response    = requests.get(sci_hub_url)
        name = doi.replace("/", "_") + ".pdf"
        path = os.path.join(download_dest, name)
        return download_response(response, path, "se"), path

    except:
        try:
            sci_hub_url = "https://sci-hub.ru/"
            sci_hub_url += doi

            response = requests.get(sci_hub_url)

            name = doi.replace("/", "_") + ".pdf"
            path = os.path.join(download_dest, name)
            return download_response(response, path, "ru"), path

        except:
            print("Article not on Sci-hub, moving on")
            return False, None

def bioArxiv_download(download_dest, DOI):
    # https://www.biorxiv.org/content/10.1101/2024.03.17.583882v1.full.pdf
    url = 'http://biorxiv.org/content/' + DOI + "v1.full.pdf"
    response = requests.get(url, stream=True)

    name = DOI.replace("/", "_") + ".pdf"
    path = os.path.join(download_dest, name)

    # Write the PDF to the file
    download_response(response, path)
    print(f"Downloaded from bioRxiv: {DOI}")
    return True, path

def medrxiv_download(download_dest, DOI):
    """
    Attempt to download a PDF from medRxiv using a DOI.

    Parameters:
    - download_dest (str): The directory to save the downloaded PDF.
    - DOI (str): The DOI of the document to download.

    Returns:
    - tuple: (bool, str) indicating success status and the file path to the downloaded PDF.
    """

    # Define the initial URL with "v1"
    urls_to_try = [
        f"https://www.medrxiv.org/content/{DOI}v1.full.pdf",
        f"https://www.medrxiv.org/content/{DOI}full.pdf",
        f"https://www.medrxiv.org/content/medrxiv/early/{DOI}v1.full.pdf"
    ]
    for url in urls_to_try:
        try:
            response = requests.get(url, stream=True)

            # Check if the response is successful and content type is PDF
            if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
                name = DOI.replace("/", "_") + ".pdf"
                path = os.path.join(download_dest, name)

                # Write the PDF to the file
                with open(path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                print(f"Downloaded from medRxiv: {DOI}")
                return True, path

        except Exception as e:
            print(f"Attempt with URL {url} failed with error: {e}. Trying next URL if available.")

    # If both attempts fail, inform the user
    print(f"PDF not available on medRxiv for doi: {DOI}")
    return False, ""

def arxiv_download(doi=None, items=None, download_dest=".", full_lib=False, title=None):
    """
    Attempt to download a PDF from arXiv or alternative sources using a DOI or title.

    Parameters:
    - doi (str, optional): The DOI of the paper to download.
    - items: Collection of items to consider for downloading. Used if `full_lib` is True.
    - download_dest (str): The directory to save the downloaded PDF.
    - full_lib (bool): Whether to perform a full library scan for matching titles.
    - title (str, optional): The title of the paper, used if DOI is not available.

    Returns:
    - tuple: (bool, str) indicating success status and the file path to the downloaded PDF.
    """
    print("Trying to download via arXiv...")
    downloaded = False
    download_dest = ensure_download_dest_is_valid(download_dest)
    client = arxiv.Client()  # Instantiate the arXiv client

    try:
        if not full_lib:
            if title:
                vector1 = text_to_vector(title)
                search = arxiv.Search(query=f'ti:"{title}"', max_results=10, sort_by=arxiv.SortCriterion.Relevance)
                for result in client.results(search):
                    vector2 = text_to_vector(result.title)
                    cosine = get_cosine(vector1, vector2)
                    if cosine > .85:
                        print(f"ArXiv match found for {title}: {result.entry_id}")
                        pdf_name = result.download_pdf(dirpath=download_dest)
                        pdf_path = os.path.join(download_dest, pdf_name)
                        downloaded = True
                        return downloaded, pdf_path
                # Attempt alternative downloads if no arXiv match is found
                if not downloaded:
                    print("Trying Sci-hub...")
                    downloaded, pdf_path = scihub_download(download_dest, doi)
                    if downloaded:
                        return downloaded, pdf_path
                if not downloaded:
                    print("Trying medArxiv...")
                    downloaded, pdf_path = medrxiv_download(download_dest, doi)
                    if downloaded:
                        return downloaded, pdf_path
                if not downloaded:
                    print("Trying bioArxiv...")
                    downloaded, pdf_path = bioArxiv_download(download_dest, doi)
                    if downloaded:
                        return downloaded, pdf_path
        else:
            # Full library scan and match logic
            for item in items:
                if item['data']['itemType'] == 'journalArticle':
                    text1 = item['data'].get('title', '')
                    vector1 = text_to_vector(text1)
                    search = arxiv.Search(query='ti:"' + text1 + '"', max_results=10, sort_by=arxiv.SortCriterion.Relevance)
                    for result in search.results(): # To do: replace with Client.results
                        vector2 = text_to_vector(result.title)
                        cosine = get_cosine(vector1, vector2)
                        if cosine > .85:
                            downloaded = True
                            print(f"ArXiv match found for {text1}: {result.entry_id}")
                            result.download_pdf(dirpath=download_dest)
                            break
                    if not downloaded:
                        downloaded, path = scihub_download(download_dest, item['data'].get('doi', ''))
                    if not downloaded:
                        downloaded, path = medrxiv_download(download_dest, item['data'].get('doi', ''))
                    if downloaded:
                        doi = item['data'].get('doi', '')
                        pdf_path = os.path.join(download_dest, f"{doi.replace('/', '_')}.pdf")
                        return downloaded, pdf_path
    except Exception as e:
        print(f"Error processing arXiv download: {e}")

    if downloaded:
        return downloaded, pdf_path # Not ref. before assignment - ignore the warning
    else:
        return downloaded, None