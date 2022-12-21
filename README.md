pyserpZotero
============
![](https://i.imgur.com/bHS0mPZs.png)

Google Scholar citation download, parsing, Bibtex export, and Zotero cloud upload via serpAPI.

  * GitHub Repo: https://github.com/hack-r/pyserpZotero
  * PyPI Package: https://pypi.org/project/pyserpZotero/
  * serpAPI: https://serpAPI.com
  * Zotero: https://zotero.org

What does it do?
----------------

*pyserpZotero* offers the following functions for (semi-) automating literature review:

* pyserpCite Module
  * *serpZot* (class) - Instantiates a serpZot object for API management. 
    * *searchScholar* - Searches Google Scholar for papers corresponding to 1 or more search terms and captures their identifiers.
    * *search2Zotero* - Pulls references from Google using identifiers from *searchScholar*, converts to Bibtex via CrossRef, reformats for Zotero, and uploads to your Zotero cloud libary (results will automatically sync to any connect desktop applications).
    * *cleanZot* - Attempt to remove/replace broken LaTex and other formatting in titles. 
    * *arxivDownload* - Checks Arxiv to see if items in your Zotero library have free PDFs available. Downloads matching PDF's from Arxiv, attaches them to the corresponding library items, and uploads the changes to Zotero.

Why serpAPI?
----------------

I'm not a shill for their company, but after a decade of scraping data I've gotten tired of code breaking due to upstream changes, dealing with 
proxies, and concerns over intellectual property. serpAPI handles those things for you. They offer a free tier, which is currently 100 searches 
per month and decent pricing. If there are other, comparable services feel free to mention them in an "Issue" and perhaps I'll be able to add 
support.

How to Configure?
----------------

You'll need to provide an API key for serpAPI and Zotero, as well as a Zotero library Id. You can either provide these directly as arguments to 
the functions or manage them more securely via a YAML configuration file, as in the *Example Usage* below.

How to Use?
----------------

See quickstartDemo.ipynb for a Jupyter notebook demonstration or checkout the example below:

## Example Usage
----------------


    #### Build a list of search terms:
    TERMS = ['reinforcement learning', 'traveling salesman', 'nowcasting', 'propensity score']

    MIN_YEAR = "2010" # Oldest year to search
    SAVE_BIB = False  # Save a Bibtex file (.bib)?
    USE_ZOT  = True   # Upload to Zotero?
    CLEAN    = False  # Attempt to remove/repair broken LaTex and other formatting 


    #### Load libraries
    from box import Box

    import importlib
    import pyserpZotero
    import yaml

    importlib.reload(pyserpZotero)

    #### Import Credentials from Your YAML File
    with open("config.yaml", "r") as ymlfile:
        cfg = Box(yaml.safe_load(ymlfile), default_box=True, default_box_attr=None)

    API_KEY = cfg.API_KEY
    ZOT_ID  = cfg.ZOT_ID
    ZOT_KEY = cfg.ZOT_KEY

    #### Instantiate a serpZot object for API management
    citeObj = pyserpZotero.serpZot(API_KEY  = API_KEY, 
                                 ZOT_ID   = ZOT_ID, 
                                 ZOT_KEY  = ZOT_KEY)

    #### Call the search method
    for i in range(len(TERMS)):
        print(citeObj.searchScholar(TERM     = TERMS[i], 
                                    MIN_YEAR = MIN_YEAR,
                                    SAVE_BIB = SAVE_BIB))
        print("This should've returned 0 (sucess)")
        # Upload the parsed results
        print(citeObj.search2Zotero())


    #### Clean Ugly Raw LaText (as Much as Possible)
    if CLEAN:
        citeObj.cleanZot(ZOT_ID      = ZOT_ID, 
                         ZOT_KEY     = ZOT_KEY,
                         SEARCH_TERM = "\\") # optional (defaults to all items)

    #### Check Arxiv for Free PDFs of Papers and Attach / Upload Them To Zotero
    citeObj.arxivDownload()
