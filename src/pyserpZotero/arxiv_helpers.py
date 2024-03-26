from helpers import get_cosine, text_to_vector
from urllib.parse import urlparse
import arxiv
import os
import re
import requests
import tempfile

# Assuming your download function looks something like this
def download_pdf(url):
    response = requests.get(url)
    if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
        # Use NamedTemporaryFile to automatically handle the file creation
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(response.content)
        temp_file.close()
        return temp_file.name
    return None

def downloadResponse(response, path, server="se"):
    try:
        if response.headers.get('content-type') == "application/pdf":
            with open(path, "wb") as f:
                f.write(response.content)
            return True
        elif "application/pdf" in response.text:
            if server == "se":
                pdf_link = "https://sci-hub.se" + re.findall('src=".*\.pdf.*"', response.text)[0].split('"')[1].split('#')[0]
            else:
                pdf_link = "https://sci-hub.ru" + re.findall('src=".*\.pdf.*"', response.text)[0].split('"')[1].split('#')[0]
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
    # Check if download_dest is a valid path
    if not isinstance(download_dest, str) or not download_dest.strip():
        download_dest = "."

    # Ensure download_dest exists
    os.makedirs(download_dest, exist_ok=True)

    # Normalize the path to remove any redundant separators, etc.
    download_dest = os.path.normpath(download_dest)

    return download_dest


def sciHubDownload(download_dest, DOI):
    try:
        sci_hub_url = "https://sci-hub.se/" + DOI
        response    = requests.get(sci_hub_url)
        name = DOI.replace("/", "_") + ".pdf"
        path = os.path.join(download_dest, name)
        return downloadResponse(response, path, "se"), path

    except:
        try:
            sci_hub_url = "https://sci-hub.ru/"
            sci_hub_url += DOI

            response = requests.get(sci_hub_url)

            name = DOI.replace("/", "_") + ".pdf"
            path = os.path.join(download_dest, name)
            return downloadResponse(response, path, "ru"), path

        except:
            print("Article not on Sci-hub, moving on")
            return False, None


def medRxivDownload(download_dest, DOI):
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
    print(f"PDF not available on medRxiv for DOI: {DOI}")
    return False, ""

def arxivDownload(doi=None, items=None, download_dest=".", full_lib=False, title=None):
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
                        result.download_pdf(dirpath=download_dest)
                        pdf_name = result.entry_id.split('/')[-1] + ".pdf"
                        pdf_path = os.path.join(download_dest, pdf_name)
                        downloaded = True
                        return downloaded, pdf_path
                # Attempt alternative downloads if no arXiv match is found
                if not downloaded:
                    print("Trying Sci-hub...")
                    downloaded, pdf_path = sciHubDownload(download_dest, doi)
                    if downloaded:
                        return downloaded, pdf_path
                if not downloaded:
                    print("Trying medArxiv...")
                    downloaded, pdf_path = medRxivDownload(download_dest, doi)
                    if downloaded:
                        return downloaded, pdf_path
        else:
            # Full library scan and match logic
            for item in items:
                if item['data']['itemType'] == 'journalArticle':
                    text1 = item['data'].get('title', '')
                    vector1 = text_to_vector(text1)
                    search = arxiv.Search(query='ti:"' + text1 + '"', max_results=10, sort_by=arxiv.SortCriterion.Relevance)
                    for result in search.results():
                        vector2 = text_to_vector(result.title)
                        cosine = get_cosine(vector1, vector2)
                        if cosine > .85:
                            downloaded = True
                            print(f"ArXiv match found for {text1}: {result.entry_id}")
                            result.download_pdf(dirpath=download_dest)
                            break
                    if not downloaded:
                        downloaded, path = sciHubDownload(download_dest, item['data'].get('DOI', ''))
                    if not downloaded:
                        downloaded, path = medRxivDownload(download_dest, item['data'].get('DOI', ''))
                    if downloaded:
                        doi = item['data'].get('DOI', '')
                        pdf_path = os.path.join(download_dest, f"{doi.replace('/', '_')}.pdf")
                        return downloaded, pdf_path
    except Exception as e:
        print(f"Error processing arXiv download: {e}")

    if downloaded:
        return downloaded, pdf_path
    else:
        return downloaded, None