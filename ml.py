from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

def rank_by_similarity(user_texts, candidate_texts):
    corpus = user_texts + candidate_texts
    tfidf = TfidfVectorizer(stop_words="english").fit_transform(corpus)

    user_vec = tfidf[:len(user_texts)].mean(axis=0)
    scores = cosine_similarity(user_vec, tfidf[len(user_texts):])[0]
    return scores
