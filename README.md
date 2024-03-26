pyserpZotero
============
![](https://i.imgur.com/bHS0mPZs.png)

Google Scholar citation download, parsing, Bibtex export, search for free PDFs, and Zotero cloud upload. SerpAPI is leveraged for stable access to Google Scholar without IP throttling.

  * Docs:         https://pyserpzotero.readthedocs.io
  * GitHub Repo:  https://github.com/hack-r/pyserpZotero
  * PyPI Package: https://pypi.org/project/pyserpZotero/
  * SerpAPI:      https://serpAPI.com
  * Zotero:       https://zotero.org


What does it do?
----------------

pyserpZotero is a sophisticated Python library designed to automate the management of scholarly literature citations and PDF downloads. It leverages the power of SerpAPI for reliable access to Google Scholar and utilizes the Zotero service for efficient citation management. The library simplifies the process of searching for academic papers, downloading them (where available for free), and organizing citations directly into your Zotero library.

*pyserpZotero* offers the following functions for (semi-) automating literature review:

* *SerpZot* (class) - Instantiates a SerpZot object for API management. 
  * ***SearchScholar*** - Searches Google Scholar for papers corresponding to 1 or more search terms and captures their identifiers.
  * ***Search2Zotero*** - Pulls references from Google using identifiers from *SearchScholar*, converts to Bibtex via CrossRef, reformats for Zotero, looks for PDFs, and uploads to your Zotero cloud library (results will automatically sync to the desktop client, if installed).
  * ***CleanZot*** - Attempt to remove/replace broken LaTex and other formatting in titles. 


Why SerpAPI?
----------------

I'm not a shill for their company, but after a decade of scraping data I've gotten tired of code breaking due to upstream changes, dealing with 
proxies, and concerns over intellectual property. SerpAPI handles those things for you. They offer a free tier, which is currently 100 searches 
per month and decent pricing.


How to configure it?
----------------

You'll need to provide an API key for serpAPI and Zotero, as well as a Zotero library Id. You can either provide these directly as arguments to 
the functions, via the interactive mode, or manage them more securely via a YAML configuration file, as in the *Example Usage* below.


How to use it?
----------------

Beginning with v1.1 an interactive mode is available by running the main file (pyserpZotero.py). See quickstart.ipynb for a Jupyter notebook demonstration of API access.


What's new?
----------------

March 2024: Added support for additional portals and PDF sources, including **medArxiv and bioRxiv**. Improved matching of citations to Arxiv PDFs. 


Why do you sometimes align assignment operators across lines like that?
----------------

As a data scientist, I'm a programming polyglot and long-time R programmer. Following top style guides for R, some of us like our code to be readable by human beings without wasting much time on it - it's a trick for easily making the code structured.