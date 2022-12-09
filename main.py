# Load libraries
import pyserpCite
import yaml

from box import Box

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
print(citeObj.searchScholar(TERM = "neurocognitive", MIN_YEAR = "1990"))
print("This should've returned 0 (sucess)")

# Upload the parsed results
print(citeObj.search2Zotero())
