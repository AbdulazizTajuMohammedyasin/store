import pandas as pd

from sklearn.metrics.pairwise import cosine_similarity

from products.models import (
    Customer,
    OrderItem,
)

from recommendations.models import (
    UserRecommendation,
)


def build_interaction_matrix():
    data = []

    order_items = (
        OrderItem.objects
        .select_related(
            "order__customer",
            "product"
        )
    )

    for item in order_items:
        data.append({
            "customer_id": item.order.customer_id,
            "product_id": item.product_id,
            "interaction": 1
        })

    if not data:
        return None

    df = pd.DataFrame(data)

    return df.pivot_table(
        index="customer_id",
        columns="product_id",
        values="interaction",
        aggfunc="sum",
        fill_value=0
    )


def collaborative_filtering():
    matrix = build_interaction_matrix()

    if matrix is None:
        return

    # Product × Product similarity matrix
    similarity_matrix = cosine_similarity(matrix.T)

    similarity_df = pd.DataFrame(
        similarity_matrix,
        index=matrix.columns,
        columns=matrix.columns
    )

    recommendations = []

    UserRecommendation.objects.all().delete()

    for customer in Customer.objects.all():

        if customer.id not in matrix.index:
            continue

        purchased_products = set(
            matrix.loc[customer.id][
                matrix.loc[customer.id] > 0
            ].index
        )

        scores = {}

        for purchased_product in purchased_products:

            similar_products = similarity_df[purchased_product]

            for product_id, similarity_score in similar_products.items():

                if product_id == purchased_product:
                    continue

                if product_id in purchased_products:
                    continue

                scores[product_id] = (
                    scores.get(product_id, 0)
                    + similarity_score
                )

        top_products = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        for product_id, score in top_products:
            recommendations.append(
                UserRecommendation(
                    customer=customer,
                    product_id=product_id,
                    score=score
                )
            )

    UserRecommendation.objects.bulk_create(
        recommendations
    )