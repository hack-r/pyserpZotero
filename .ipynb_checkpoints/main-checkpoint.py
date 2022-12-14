########
# Build a list of search terms:
TERMS = ['Reinforcement learning', 'traveling salesman', 'xgb traveling salesman', 'machine learning optimization route']

TERMS = ['kansas pipeline','kansas capitali','immigration 1994','immigration 1995','immigration 1996']

MIN_YEAR = "1900" # Oldest year to search
SAVE_BIB = False  # Save a Bibtex file (.bib)?
USE_ZOT  = True   # Upload to Zotero?

########
# Load libraries
from box import Box

import cleanZot
import importlib
import pyserpCite
import yaml

importlib.reload(pyserpCite)

# Import Credentials from Your YAML File
with open("config.yaml", "r") as ymlfile:
    cfg = Box(yaml.safe_load(ymlfile), default_box=True, default_box_attr=None)

API_KEY = cfg.API_KEY
ZOT_ID  = cfg.ZOT_ID
ZOT_KEY = cfg.ZOT_KEY

# Instantiate a serpZot object for API management
citeObj = pyserpCite.serpZot(API_KEY  = API_KEY, 
                             ZOT_ID   = ZOT_ID, 
                             ZOT_KEY  = ZOT_KEY)

# Call the search method
for i in range(len(TERMS)):
    print(citeObj.searchScholar(TERM     = TERMS[i], 
                                MIN_YEAR = MIN_YEAR,
                                SAVE_BIB = SAVE_BIB))
    print("This should've returned 0 (sucess)")
    # Upload the parsed results
    print(citeObj.search2Zotero())
    

# Clean Ugly Raw LaText (as Much as Possible)
CLEAN = False
if CLEAN:
    cleanZot.serpZot(ZOT_ID      = ZOT_ID, 
                     ZOT_KEY     = ZOT_KEY,
                     SEARCH_TERM = "\\") # optional (defaults to all items)