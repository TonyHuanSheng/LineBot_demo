import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import pandas as pd


def get_tfidf_recommendation(id):
    data = pd.read_csv("id_pair.csv")
    a = data.index[data['id'] == id][0]
    z = pickle.load(open("res.pkl", "rb"))
    similarity_matrix = cosine_similarity(z[a:a + 1], z)[0]
    related_product_indices = similarity_matrix.argsort()[-6:-1][::-1]

    res_id = data.iloc[related_product_indices]['id']
    return list(res_id)