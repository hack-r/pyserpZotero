# helpers.py
from collections import Counter
from wordcloud import STOPWORDS

import math
import re

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