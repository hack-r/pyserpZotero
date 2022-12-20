# Libraries
from box import Box
from pyzotero import zotero

import sys
import yaml

#

def cleanZot(ZOT_ID = "", ZOT_KEY = "",SEARCH_TERM=""):
    # Connect to Zotero
    zot = zotero.Zotero(ZOT_ID, 'user', ZOT_KEY)
    
    zot.add_parameters(q=SEARCH_TERM)
    items = zot.everything(zot.items())
    
    message = "Number of items retreived from your library:" + str(len(items))
    print(message)
    
    n=0
    for item in items:
        n = n+1
        message2 = "Processing number: " + str(n)
        # Clean LaTex and similar garbage
        item['data']['title'] = item['data']['title'].replace("{","")
        item['data']['title'] = item['data']['title'].replace("}","")
        item['data']['title'] = item['data']['title'].replace("$\less","")
        item['data']['title'] = item['data']['title'].replace("$scp","")
        item['data']['title'] = item['data']['title'].replace("$\greater","")
        item['data']['title'] = item['data']['title'].replace("/scp","")
        item['data']['title'] = item['data']['title'].replace("$$","")
        item['data']['title'] = item['data']['title'].replace("$","")
        item['data']['title'] = item['data']['title'].replace("\\upkappa","k")
        item['data']['title'] = item['data']['title'].replace("\\upalpha","α")
        item['data']['title'] = item['data']['title'].replace("\\textdollar","$") # must come after replacement of $
        item['data']['title'] = item['data']['title'].replace("\\mathplus","+")
        item['data']['title'] = item['data']['title'].replace('\\textquotedblleft','"')
        item['data']['title'] = item['data']['title'].replace('\\textquotedblright','"')
        item['data']['title'] = item['data']['title'].replace("\\textendash","-")
        item['data']['title'] = item['data']['title'].replace("$\textbackslashsqrt","")
        item['data']['title'] = item['data']['title'].replace("\\textbackslashsqrt","")
        item['data']['title'] = item['data']['title'].replace("\\textbackslash","")
        item['data']['title'] = item['data']['title'].replace("\textemdash","-")
        item['data']['title'] = item['data']['title'].replace("\\lbraces","")
        item['data']['title'] = item['data']['title'].replace("\\lbrace=","")
        item['data']['title'] = item['data']['title'].replace("\\rbrace=","")
        item['data']['title'] = item['data']['title'].replace("\\rbrace","")
        item['data']['title'] = item['data']['title'].replace("\\rbrace","")
        item['data']['title'] = item['data']['title'].replace("$\sim$","~")
        item['data']['title'] = item['data']['title'].replace("$\\sim$","~")
        item['data']['title'] = item['data']['title'].replace("\\&amp","&")
        item['data']['title'] = item['data']['title'].replace("\&amp","&")
        item['data']['title'] = item['data']['title'].replace("\\mathsemicolon",";")
        item['data']['title'] = item['data']['title'].replace("\\mathcolon",":")
        item['data']['title'] = item['data']['title'].replace("\mathsemicolon",";")
        item['data']['title'] = item['data']['title'].replace("\mathcolon",":")
        item['data']['title'] = item['data']['title'].replace("\\#",":")

    # Update the cloud with the improvements
    print("Updating your cloud library...")
    zot.update_items(items)
    
    print("Done! I hope this made things more readable.")
    # Return 0
    return 0