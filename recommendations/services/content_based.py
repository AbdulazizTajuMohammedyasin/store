from products.models import Product
from recommendations.models import ProductRecommendation
from django.db import transaction

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

MIN_SIMILARITY = 0.15
MAX_RECOMMENDATIONS = 8

def content_based():
    
    """
    Generate content-based product recommendations using
    TF-IDF and cosine similarity.

    Existing recommendations are replaced atomically.
    """

    products = list(Product.objects.select_related("collection"))
    if not products:
        ProductRecommendation.objects.all().delete()
        return
    
    df = pd.DataFrame([
            {
                'id': p.id,
                'title': p.title,
                'text': f"{p.title} {p.title} {p.collection.title} {p.description or ''}"
            }
            for p in products
        ])

    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 2),
        max_df=0.8
    )
    tfidf_matrix = vectorizer.fit_transform(df['text'])
    similarity_matrix = cosine_similarity(tfidf_matrix)


    

    recommendations = []
    
    

    for i, product in enumerate(products):

        similar_items = sorted(
            enumerate(similarity_matrix[i]),
            key=lambda x: x[1],
            reverse=True
        )[1:]

        count = 0

        for j, score in similar_items:

            if score < MIN_SIMILARITY:
                continue

            recommendations.append(
                ProductRecommendation(
                    product=product,
                    recommended_product=products[j],
                    score=score
                )
            )

            count += 1

            if count == MAX_RECOMMENDATIONS:
                break
    with transaction.atomic():
        ProductRecommendation.objects.all().delete()
        ProductRecommendation.objects.bulk_create(recommendations)