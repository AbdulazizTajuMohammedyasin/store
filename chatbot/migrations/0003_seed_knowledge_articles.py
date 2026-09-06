from django.db import migrations

PLACEHOLDER_NOTICE = (
    "[Placeholder content generated during setup — please review and "
    "replace with the store's real policy text in Django admin.]"
)

ARTICLES = [
    {
        "title": "Shipping Policy",
        "category": "shipping",
        "content": f"""{PLACEHOLDER_NOTICE}

Standard shipping takes 3-7 business days. Express shipping takes
1-3 business days and is available at checkout for an additional fee.
Orders over $50 qualify for free standard shipping. Orders are
processed within 1-2 business days before shipping.""",
    },
    {
        "title": "Return & Refund Policy",
        "category": "returns",
        "content": f"""{PLACEHOLDER_NOTICE}

Items can be returned within 30 days of delivery for a full refund,
provided they are unused and in their original packaging. To start a
return, contact customer support with your order number. Refunds are
issued to the original payment method within 5-10 business days after
the returned item is received.""",
    },
    {
        "title": "Payment Methods",
        "category": "payment",
        "content": f"""{PLACEHOLDER_NOTICE}

We accept major credit and debit cards. Payment is charged when your
order is placed. All transactions are processed securely and we never
store your full card details.""",
    },
    {
        "title": "How to Track Your Order",
        "category": "faq",
        "content": f"""{PLACEHOLDER_NOTICE}

You can track your order from the "My Orders" page after logging in,
which shows the current status of each order. You'll also receive an
email confirmation when your order ships.""",
    },
    {
        "title": "How to Contact Customer Support",
        "category": "faq",
        "content": f"""{PLACEHOLDER_NOTICE}

For help with an order, account, or product question, contact
customer support by email. Support is available on business days and
typically responds within 24-48 hours.""",
    },
]


def seed_articles(apps, schema_editor):
    KnowledgeArticle = apps.get_model("chatbot", "KnowledgeArticle")

    for article in ARTICLES:
        KnowledgeArticle.objects.get_or_create(
            title=article["title"],
            defaults={
                "category": article["category"],
                "content": article["content"],
            },
        )


def remove_seeded_articles(apps, schema_editor):
    KnowledgeArticle = apps.get_model("chatbot", "KnowledgeArticle")
    KnowledgeArticle.objects.filter(
        title__in=[article["title"] for article in ARTICLES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0002_knowledgearticle"),
    ]

    operations = [
        migrations.RunPython(seed_articles, remove_seeded_articles),
    ]
