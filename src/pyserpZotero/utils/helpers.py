# utils/helpers.py
from collections import Counter
from pyzotero import zotero
from wordcloud import STOPWORDS

import math
import re


def cleanZot(self, search_term="", field="title"):
    # Get keys / id from Self
    # Ignore any errors about it not being used
    id = self.ZOT_ID
    key = self.ZOT_KEY

    # Connect to Zotero
    zot = zotero.Zotero(id, 'user', key)

    zot.add_parameters(q=search_term)
    items = zot.everything(zot.items())

    message = "Number of items retreived from your library:" + str(len(items))
    print(message)

    n = 0
    for item in items:
        n = n + 1
        message2 = "Processing number: " + str(n)
        try:
            # Clean LaTex and similar garbage
            item['data'][field] = item['data'][field].replace("{", "")
            item['data'][field] = item['data'][field].replace("}", "")
            item['data'][field] = item['data'][field].replace("$\less", "")
            item['data'][field] = item['data'][field].replace("$scp", "")
            item['data'][field] = item['data'][field].replace("$\greater", "")
            item['data'][field] = item['data'][field].replace("/scp", "")
            item['data'][field] = item['data'][field].replace("$$", "")
            item['data'][field] = item['data'][field].replace("$", "")
            item['data'][field] = item['data'][field].replace("\\upkappa", "k")
            item['data'][field] = item['data'][field].replace("\\upalpha", "α")
            item['data'][field] = item['data'][field].replace("\\textdollar",
                                                              "$")  # must come after replacement of $
            item['data'][field] = item['data'][field].replace("\\mathplus", "+")
            item['data'][field] = item['data'][field].replace('\\textquotedblleft', '"')
            item['data'][field] = item['data'][field].replace('\\textquotedblright', '"')
            item['data'][field] = item['data'][field].replace('{\\textquotesingle}', "'")
            item['data'][field] = item['data'][field].replace('{\\\textquotesingle}', "'")
            item['data'][field] = item['data'][field].replace('{\\\\textquotesingle}', "'")
            item['data'][field] = item['data'][field].replace("\\textendash", "-")
            item['data'][field] = item['data'][field].replace("$\textbackslashsqrt", "")
            item['data'][field] = item['data'][field].replace("\\textbackslashsqrt", "")
            item['data'][field] = item['data'][field].replace("\\textbackslash", "")
            item['data'][field] = item['data'][field].replace("\textemdash", "-")
            item['data'][field] = item['data'][field].replace("\\lbraces", "")
            item['data'][field] = item['data'][field].replace("\\lbrace=", "")
            item['data'][field] = item['data'][field].replace("\\rbrace=", "")
            item['data'][field] = item['data'][field].replace("\\rbrace", "")
            item['data'][field] = item['data'][field].replace("\\rbrace", "")
            item['data'][field] = item['data'][field].replace("$\sim$", "~")
            item['data'][field] = item['data'][field].replace("$\\sim$", "~")
            item['data'][field] = item['data'][field].replace("\\&amp", "&")
            item['data'][field] = item['data'][field].replace("\&amp", "&")
            item['data'][field] = item['data'][field].replace("\\mathsemicolon", ";")
            item['data'][field] = item['data'][field].replace("\\mathcolon", ":")
            item['data'][field] = item['data'][field].replace("\mathsemicolon", ";")
            item['data'][field] = item['data'][field].replace("\mathcolon", ":")
            item['data'][field] = item['data'][field].replace("\\#", ":")
            item['data'][field] = item['data'][field].replace("\\textregistered", "®")
            item['data'][field] = item['data'][field].replace("\textregistered", "®")
            item['data'][field] = item['data'][field].replace("\\\textregistered", "®")
            item['data'][field] = item['data'][field].replace("#1I/`", "'")
            item['data'][field] = item['data'][field].replace("1I/", "'")
            item['data'][field] = item['data'][field].replace("\1I/", "'")  # {\’{\i}}   {\’{\a}}   {\’{o}}
            item['data'][field] = item['data'][field].replace("{\’{\a}}", "a")
            item['data'][field] = item['data'][field].replace("{\’{\e}}", "e")
            item['data'][field] = item['data'][field].replace("{\’{\i}}", "i")
            item['data'][field] = item['data'][field].replace("{\’{\o}}", "o")
            item['data'][field] = item['data'][field].replace("{\’{a}}", "a")
            item['data'][field] = item['data'][field].replace("{\’{e}}", "e")
            item['data'][field] = item['data'][field].replace("{\’{i}}", "i")
            item['data'][field] = item['data'][field].replace("{\’{o}}", "o")
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
    ''' # Credit: https://stackoverflow.com/questions/15173225/calculate-cosine-similarity-given-2-sentence-strings
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
    WORD = re.compile(r"\w+")
    words = WORD.findall(text)
    return Counter(words)