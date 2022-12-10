########
# Build a list of search terms:
TERMS = ['neurocognitive dose','memory improve medicine',
        'Lion Mane memory', 'Lion Mane cognitive', 'magnesium memory',
        'patient trial memory', 'intellectual disability effective',
        'intellectual disability internal medicine',
        'intellectual disability nootropic', 'nootropic medicine',
        'nmda piracetam', 'memory enhancement', 'clinical cognitive',
        'alzheimer clinical','alzheimer peptide', 'effective treatment alzheimer',
        'improved cognitive tbi', 'traumatic brain treament dose']

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
    print(citeObj.searchScholar(TERM = TERMS[i], MIN_YEAR = "1990"))
    print("This should've returned 0 (sucess)")
    # Upload the parsed results
    print(citeObj.search2Zotero())
