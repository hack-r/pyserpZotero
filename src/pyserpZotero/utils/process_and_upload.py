from bibtexparser.bparser import BibTexParser
from datetime import date, datetime

import bibtexparser
import os

def processBibsAndUpload(self, doiSet, zot, items, FIELD, citation):
    """
    This function will download pdfs and citations related to all DOIs present in the DOI set. It will also
    upload the results to Zotero

    Parameters:
    - doiSet (set): The set of DOIs.
    - zot (Zotero Object): The place to upload the relevant findings.
    - items (list): List of all present items in Zotero.
    - citation (Boolean): Whether to create citation (True) or to download (False).

    Returns:
    - (int): Status code indicating success (0) or failure (non-zero).
    """

    if citation:
        print("Starting citation thread")
        for doi, abstract in doiSet:
            template = zot.item_template('journalArticle')  # Set Template
            curl_str = 'curl -LH "Accept: application/x-bibtex" http://dx.doi.org/' + doi
            result = os.popen(curl_str).read()
            if not result:
                # medArxiv, bioarxiv and arxiv use this link to get the citation details
                curl_str = 'curl -LH "Accept: application/x-bibtex" https://doi.org/' + doi
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

            # # Parse Names into Template/Data
            # try:
            try:
                if 'author' not in bib_dict:
                    bib_dict['author'] = ["Unknown, Unknown"]
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
                template['doi'] = str(doi)
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
                template['abstractNote'] = abstract
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
                no_author_found = False
                try:
                    num_authors = len(bib_dict['author'])
                except:
                    num_authors = 1
                    bib_dict['author'] = ['Unknown Unknown']
                    no_author_found = True
                template['creators'] = []

                for a in bib_dict['author']:
                    split = bibtexparser.customization.splitname(a, strict_mode=False)
                    template['creators'].append(
                        {'creatorType': 'author', 'firstName': split['first'][0], 'lastName': split['last'][0]})
                print(template)
                if template["doi"] in self.DOI_HOLDER:
                    print("Not citation uploading since it's already present in Zotero")
                    continue
                if no_author_found:
                    print("No authors found for this paper, skipping upload to zotero")
                    continue
                if template.get("title", None) == None:
                    print("Paper does not have a title. Skipping upload to Zotero")
                    continue
                cite_upload_response = zot.create_items([template])
                zotero_item_key = []
                if 'successful' in cite_upload_response:
                    for key in cite_upload_response['successful']:
                        zotero_item_key.append(cite_upload_response['successful'][key]['key'])

                print("ZOTERO ITEM KEYS: ", zotero_item_key)
                with self.lock:
                    self.CITATION_DICT[doi] = (zotero_item_key, bib_dict)
                    print(f"\n\n\nCITATION DICT: \n{self.CITATION_DICT}")

            except Exception as e:
                print(f"An error occurred while parsing: {e}")

        with self.lock:
            self.CITATION_DICT["END"] = None
    else:
        print("Starting downloading thread")
        full_lib = False
        if self.enable_pdf_download:
            self.attempt_pdf_download(items=items, full_lib=full_lib)

    return 0
