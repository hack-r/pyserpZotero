# helpers.py
from collections import Counter
from pyzotero import zotero
from wordcloud import STOPWORDS

import math
import re


def cleanZot(self, SEARCH_TERM="", FIELD="title"):
    # Get keys / id from Self
    # Ignore any errors about it not being used
    id = self.ZOT_ID
    key = self.ZOT_KEY

    # Connect to Zotero
    zot = zotero.Zotero(id, 'user', key)

    zot.add_parameters(q=SEARCH_TERM)
    items = zot.everything(zot.items())

    message = "Number of items retreived from your library:" + str(len(items))
    print(message)

    n = 0
    for item in items:
        n = n + 1
        message2 = "Processing number: " + str(n)
        try:
            # Clean LaTex and similar garbage
            item['data'][FIELD] = item['data'][FIELD].replace("{", "")
            item['data'][FIELD] = item['data'][FIELD].replace("}", "")
            item['data'][FIELD] = item['data'][FIELD].replace("$\less", "")
            item['data'][FIELD] = item['data'][FIELD].replace("$scp", "")
            item['data'][FIELD] = item['data'][FIELD].replace("$\greater", "")
            item['data'][FIELD] = item['data'][FIELD].replace("/scp", "")
            item['data'][FIELD] = item['data'][FIELD].replace("$$", "")
            item['data'][FIELD] = item['data'][FIELD].replace("$", "")
            item['data'][FIELD] = item['data'][FIELD].replace("\\upkappa", "k")
            item['data'][FIELD] = item['data'][FIELD].replace("\\upalpha", "α")
            item['data'][FIELD] = item['data'][FIELD].replace("\\textdollar",
                                                              "$")  # must come after replacement of $
            item['data'][FIELD] = item['data'][FIELD].replace("\\mathplus", "+")
            item['data'][FIELD] = item['data'][FIELD].replace('\\textquotedblleft', '"')
            item['data'][FIELD] = item['data'][FIELD].replace('\\textquotedblright', '"')
            item['data'][FIELD] = item['data'][FIELD].replace('{\\textquotesingle}', "'")
            item['data'][FIELD] = item['data'][FIELD].replace('{\\\textquotesingle}', "'")
            item['data'][FIELD] = item['data'][FIELD].replace('{\\\\textquotesingle}', "'")
            item['data'][FIELD] = item['data'][FIELD].replace("\\textendash", "-")
            item['data'][FIELD] = item['data'][FIELD].replace("$\textbackslashsqrt", "")
            item['data'][FIELD] = item['data'][FIELD].replace("\\textbackslashsqrt", "")
            item['data'][FIELD] = item['data'][FIELD].replace("\\textbackslash", "")
            item['data'][FIELD] = item['data'][FIELD].replace("\textemdash", "-")
            item['data'][FIELD] = item['data'][FIELD].replace("\\lbraces", "")
            item['data'][FIELD] = item['data'][FIELD].replace("\\lbrace=", "")
            item['data'][FIELD] = item['data'][FIELD].replace("\\rbrace=", "")
            item['data'][FIELD] = item['data'][FIELD].replace("\\rbrace", "")
            item['data'][FIELD] = item['data'][FIELD].replace("\\rbrace", "")
            item['data'][FIELD] = item['data'][FIELD].replace("$\sim$", "~")
            item['data'][FIELD] = item['data'][FIELD].replace("$\\sim$", "~")
            item['data'][FIELD] = item['data'][FIELD].replace("\\&amp", "&")
            item['data'][FIELD] = item['data'][FIELD].replace("\&amp", "&")
            item['data'][FIELD] = item['data'][FIELD].replace("\\mathsemicolon", ";")
            item['data'][FIELD] = item['data'][FIELD].replace("\\mathcolon", ":")
            item['data'][FIELD] = item['data'][FIELD].replace("\mathsemicolon", ";")
            item['data'][FIELD] = item['data'][FIELD].replace("\mathcolon", ":")
            item['data'][FIELD] = item['data'][FIELD].replace("\\#", ":")
            item['data'][FIELD] = item['data'][FIELD].replace("\\textregistered", "®")
            item['data'][FIELD] = item['data'][FIELD].replace("\textregistered", "®")
            item['data'][FIELD] = item['data'][FIELD].replace("\\\textregistered", "®")
            item['data'][FIELD] = item['data'][FIELD].replace("#1I/`", "'")
            item['data'][FIELD] = item['data'][FIELD].replace("1I/", "'")
            item['data'][FIELD] = item['data'][FIELD].replace("\1I/", "'")  # {\’{\i}}   {\’{\a}}   {\’{o}}
            item['data'][FIELD] = item['data'][FIELD].replace("{\’{\a}}", "a")
            item['data'][FIELD] = item['data'][FIELD].replace("{\’{\e}}", "e")
            item['data'][FIELD] = item['data'][FIELD].replace("{\’{\i}}", "i")
            item['data'][FIELD] = item['data'][FIELD].replace("{\’{\o}}", "o")
            item['data'][FIELD] = item['data'][FIELD].replace("{\’{a}}", "a")
            item['data'][FIELD] = item['data'][FIELD].replace("{\’{e}}", "e")
            item['data'][FIELD] = item['data'][FIELD].replace("{\’{i}}", "i")
            item['data'][FIELD] = item['data'][FIELD].replace("{\’{o}}", "o")
        except:
            pass

    # Update the cloud with the improvements
    print("Updating your cloud library...")
    zot.update_items(items)

    print("Done! I hope this made things more readable.")
    # Return 0
    return 0


def get_cosine(vec1, vec2):
    '''
    Helper function that takes 2 vectors from text_to_vector

    :param vec1: vector from text_to_vector
    :type vec1: ve
    :param vec2: vector from text_to_vector
    '''
    vec1_keys = set(vec1.keys())
    vec2_keys = set(vec2.keys())
    vec1_updated = []
    vec2_updated = []
    # pdb.set_trace()

    for word in vec1_keys:
        if word.lower() in STOPWORDS:
            continue
        vec1_updated.append(word)

    for word in vec2_keys:
        if word.lower() in STOPWORDS:
            continue
        vec2_updated.append(word)

    vec1_updated = Counter(vec1_updated)
    vec2_updated = Counter(vec2_updated)

    intersection = set(vec1_updated.keys()) & set(vec2_updated.keys())
    numerator = sum([vec1_updated[x] * vec2_updated[x] for x in intersection])

    sum1 = sum([vec1_updated[x] ** 2 for x in list(vec1_updated.keys())])
    sum2 = sum([vec2_updated[x] ** 2 for x in list(vec2_updated.keys())])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator


def text_to_vector(text):
    '''
    Converts strings to vectors

    :param text: search term (title, etc)
    :type text: str
    '''
    # Credit: https://stackoverflow.com/questions/15173225/calculate-cosine-similarity-given-2-sentence-strings
    WORD = re.compile(r"\w+")
    words = WORD.findall(text)
    return Counter(words)