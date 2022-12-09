import pyserpCite


# Instantiate a serpZot object for API management
citeObj = pyserpCite.serpZot(API_KEY  = "", 
                           ZOT_ID   = "", 
                           ZOT_KEY  = "")

# Call the search method
print(citeObj.searchScholar(TERM = "memory oxygen treatment", MIN_YEAR = "2020"))
print("This should've returned 0 (sucess)")

# Upload the parsed results
print(citeObj.search2Zotero())
