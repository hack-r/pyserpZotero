import pyserpCite


# Instantiate a serpZot object for API management
citeObj = pyserpCite.serpZot(API_KEY  = "2d7e471867259b72fb019add2ef26d4d477a87f913ef55d90b2c649f4b8af9de", 
                           ZOT_ID   = "7032524", 
                           ZOT_KEY  = "AHUiTfE6jN7hKweV5798MSrv")

# Call the search method
print(citeObj.searchScholar(TERM = "memory oxygen treatment", MIN_YEAR = "2020"))
print("This should've returned 0 (sucess)")

# Upload the parsed results
print(citeObj.search2Zotero())