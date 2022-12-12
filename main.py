########
# Build a list of search terms:
TERMS = ['prl-8-53','time series forecasting']
MIN_YEAR = "2019"
    
########
# Load libraries
import importlib
import pyserpCite
import yaml

from box import Box

importlib.reload(pyserpCite)

# Import Credentials from Your YAML File
with open("config.yaml", "r") as ymlfile:
    cfg = Box(yaml.safe_load(ymlfile), default_box=True, default_box_attr=None)

API_KEY = cfg.API_KEY
ZOT_ID = cfg.ZOT_ID
ZOT_KEY = cfg.ZOT_KEY

# Instantiate a serpZot object for API management
citeObj = pyserpCite.serpZot(API_KEY = API_KEY, 
                           ZOT_ID = ZOT_ID, 
                           ZOT_KEY = ZOT_KEY)

# Call the search method
for i in range(len(TERMS)):
    print(citeObj.searchScholar(TERM = TERMS[i], MIN_YEAR = MIN_YEAR))
    print("This should've returned 0 (sucess)")
    # Upload the parsed results
    print(citeObj.search2Zotero())
