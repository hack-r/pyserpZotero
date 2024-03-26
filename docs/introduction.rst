Introduction
============

This section provides an overview of pyserpZotero, including its purpose, main features, and how it integrates with SerpAPI, Zotero, and various academic repositories to automate the management of scholarly literature.

**Purpose**

The aim of pyserpZotero is to automate the following tasks:

  - cleaning mangled LaTex in citations (the mangling can come from upstream issues or the exportation and importation of citation data across formats)
  - collection of citations
  - search, download, and attachment of free PDFs to citations
  - upload of PDFs to Zotero

**Strategy**

SerpAPI is leveraged to provide stable access to search results without IP throttling. As a freemium service it can be used for up to 100 searches per month at no cost.

**Possible Future Improvements**

  - proxy support as an alternative to SerpAPI
  - support for other citation managers