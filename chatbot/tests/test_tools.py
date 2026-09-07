from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from chatbot.models import KnowledgeArticle
from chatbot.services.tools import cart as cart_tools
from chatbot.services.tools import knowledge as knowledge_tools
from chatbot.services.tools import orders as order_tools
from chatbot.services.tools import recommendations as recommendation_tools
from chatbot.services.tools.products import get_product_details, search_products
from chatbot.services.tools.reviews import get_product_review_summary
from products.models import CartItem, Collection, Order, OrderItem, Product, Review

User = get_user_model()


def create_customer(username):
    user = User.objects.create_user(username=username, password="pass12345")
    return user.customer


def create_product(title, price="19.99", inventory=10, collection=None):
    collection = collection or Collection.objects.create(title="Test Collection")
    return Product.objects.create(
        title=title,
        description=f"Description for {title}",
        price=Decimal(price),
        inventory=inventory,
        collection=collection,
    )


class ProductToolsTests(TestCase):
    def setUp(self):
        self.collection = Collection.objects.create(title="Shoes")
        self.product = create_product(
            "Running Shoes", price="59.99", collection=self.collection
        )

    def test_search_products_matches_by_title(self):
        results = search_products("Running")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.product.id)
        self.assertEqual(results[0]["title"], self.product.title)

    def test_search_products_no_match(self):
        self.assertEqual(search_products("nonexistent"), [])

    def test_get_product_details_valid(self):
        details = get_product_details(self.product.id)

        self.assertEqual(details["title"], "Running Shoes")
        self.assertEqual(details["price"], "59.99")
        self.assertEqual(details["collection"], "Shoes")

    def test_get_product_details_invalid_id(self):
        details = get_product_details(999999)
        self.assertIn("error", details)


class ReviewToolsTests(TestCase):
    def setUp(self):
        self.product = create_product("Reviewed Product")

    def test_no_reviews_returns_friendly_message(self):
        result = get_product_review_summary(self.product.id)

        self.assertEqual(result["review_count"], 0)
        self.assertIsNone(result["average_rating"])

    def test_invalid_product_returns_error(self):
        result = get_product_review_summary(999999)
        self.assertIn("error", result)

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache"
            }
        }
    )
    @patch("chatbot.services.tools.reviews.GeminiClient")
    def test_summarizes_and_caches_reviews(self, MockGeminiClient):
        MockGeminiClient.return_value.summarize.return_value = "Mostly positive."

        customer1 = create_customer("reviewer1")
        customer2 = create_customer("reviewer2")
        Review.objects.create(
            product=self.product, customer=customer1, rating=5, comment="Great!"
        )
        Review.objects.create(
            product=self.product, customer=customer2, rating=3, comment="Okay."
        )

        result = get_product_review_summary(self.product.id)

        self.assertEqual(result["review_count"], 2)
        self.assertEqual(result["average_rating"], 4.0)
        self.assertEqual(result["summary"], "Mostly positive.")
        MockGeminiClient.return_value.summarize.assert_called_once()

        # second call should hit the cache, not call Gemini again
        get_product_review_summary(self.product.id)
        MockGeminiClient.return_value.summarize.assert_called_once()


class RecommendationToolsTests(TestCase):
    def test_similar_products_invalid_id(self):
        result = recommendation_tools.get_similar_products(999999)
        self.assertIn("error", result)

    def test_similar_products_finds_related_titles(self):
        collection = Collection.objects.create(title="Blocks")
        target = Product.objects.create(
            title="Wooden Building Blocks Set",
            description="Colorful wooden blocks for kids",
            price=Decimal("29.99"),
            inventory=5,
            collection=collection,
        )
        Product.objects.create(
            title="Wooden Building Blocks Deluxe Set",
            description="Bigger set of colorful wooden blocks",
            price=Decimal("49.99"),
            inventory=5,
            collection=collection,
        )
        Product.objects.create(
            title="Garden Hose",
            description="For watering plants",
            price=Decimal("15.00"),
            inventory=5,
            collection=collection,
        )

        results = recommendation_tools.get_similar_products(target.id)

        self.assertIsInstance(results, list)
        titles = [item["title"] for item in results]
        self.assertIn("Wooden Building Blocks Deluxe Set", titles)
        self.assertNotIn("Garden Hose", titles)

    def test_recommended_products_with_no_purchase_history(self):
        customer = create_customer("nopurchases")
        result = recommendation_tools.get_recommended_products_for_customer(
            customer.id
        )
        self.assertEqual(result, "No personalized recommendations are available yet.")


class CartToolsTests(TestCase):
    def setUp(self):
        self.customer = create_customer("cartcustomer")
        self.product = create_product("Cart Product", price="10.00", inventory=100)
        self.other_product = create_product(
            "Other Product", price="5.00", inventory=100
        )

    def test_view_empty_cart(self):
        self.assertEqual(cart_tools.get_cart_contents(self.customer), "The cart is empty.")

    def test_add_item_then_view_cart(self):
        cart_tools.add_item_to_cart(self.customer, self.product.id, 2)

        contents = cart_tools.get_cart_contents(self.customer)

        self.assertEqual(len(contents["items"]), 1)
        self.assertEqual(contents["items"][0]["quantity"], 2)
        self.assertEqual(contents["total_price"], "20.00")

    def test_add_item_twice_merges_quantity(self):
        cart_tools.add_item_to_cart(self.customer, self.product.id, 2)
        cart_tools.add_item_to_cart(self.customer, self.product.id, 3)

        item = CartItem.objects.get(cart=self.customer.cart, product=self.product)
        self.assertEqual(item.quantity, 5)

    def test_add_item_invalid_product(self):
        result = cart_tools.add_item_to_cart(self.customer, 999999, 1)
        self.assertIn("error", result)

    def test_add_item_invalid_quantity(self):
        result = cart_tools.add_item_to_cart(self.customer, self.product.id, 0)
        self.assertIn("error", result)

    def test_update_item_not_in_cart(self):
        result = cart_tools.update_cart_item_quantity(
            self.customer, self.product.id, 3
        )
        self.assertIn("error", result)

    def test_update_item_quantity(self):
        cart_tools.add_item_to_cart(self.customer, self.product.id, 1)
        cart_tools.update_cart_item_quantity(self.customer, self.product.id, 5)

        item = CartItem.objects.get(cart=self.customer.cart, product=self.product)
        self.assertEqual(item.quantity, 5)

    def test_remove_item(self):
        cart_tools.add_item_to_cart(self.customer, self.product.id, 1)
        result = cart_tools.remove_item_from_cart(self.customer, self.product.id)

        self.assertIn("message", result)
        self.assertFalse(
            CartItem.objects.filter(
                cart=self.customer.cart, product=self.product
            ).exists()
        )

    def test_remove_item_not_in_cart(self):
        result = cart_tools.remove_item_from_cart(self.customer, self.product.id)
        self.assertIn("error", result)

    def test_carts_are_isolated_between_customers(self):
        other_customer = create_customer("othercartcustomer")
        cart_tools.add_item_to_cart(self.customer, self.product.id, 1)

        self.assertEqual(
            cart_tools.get_cart_contents(other_customer), "The cart is empty."
        )


class OrderToolsTests(TestCase):
    def setUp(self):
        self.customer = create_customer("orderowner")
        self.other_customer = create_customer("notordeowner")
        self.product = create_product("Ordered Product", price="25.00")

        self.order = Order.objects.create(
            customer=self.customer, payment_status="C"
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            unit_price=Decimal("25.00"),
        )

    def test_list_orders_for_customer(self):
        results = order_tools.list_orders_for_customer(self.customer)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.order.id)

    def test_list_orders_for_customer_with_no_orders(self):
        result = order_tools.list_orders_for_customer(self.other_customer)
        self.assertEqual(result, "No orders found.")

    def test_get_order_details_for_owner(self):
        details = order_tools.get_order_details_for_customer(
            self.customer, self.order.id
        )

        self.assertEqual(details["id"], self.order.id)
        self.assertEqual(len(details["items"]), 1)
        self.assertEqual(details["items"][0]["quantity"], 2)
        self.assertEqual(details["items"][0]["total_price"], "50.00")

    def test_get_order_details_denies_other_customers(self):
        """
        A customer must never be able to fetch another customer's order,
        even though order_id is a plain LLM-controllable argument.
        """
        result = order_tools.get_order_details_for_customer(
            self.other_customer, self.order.id
        )
        self.assertIn("error", result)

    def test_get_order_details_invalid_id(self):
        result = order_tools.get_order_details_for_customer(self.customer, 999999)
        self.assertIn("error", result)


class KnowledgeBaseToolsTests(TestCase):
    def setUp(self):
        # A data migration seeds placeholder articles into every fresh
        # database (including the test DB), so start from a clean slate
        # for a controlled, deterministic dataset in each test.
        KnowledgeArticle.objects.all().delete()

    def _fake_embedding_for(self, text):
        # Deterministic "embedding": articles about the same topic as the
        # query get a high-similarity vector, everything else gets an
        # orthogonal one.
        if "return" in text.lower():
            return [1.0, 0.0, 0.0]
        return [0.0, 1.0, 0.0]

    @patch("chatbot.services.embeddings.embed_text")
    def test_search_ranks_most_relevant_article_first(self, mock_embed_text):
        mock_embed_text.side_effect = self._fake_embedding_for

        KnowledgeArticle.objects.create(
            title="Return Policy", category="returns", content="Returns info"
        )
        KnowledgeArticle.objects.create(
            title="Shipping Policy", category="shipping", content="Shipping info"
        )

        results = knowledge_tools.search_knowledge_base("What is your return policy?")

        self.assertEqual(results[0]["title"], "Return Policy")

    @patch("chatbot.services.embeddings.embed_text")
    def test_backfills_missing_embeddings_before_searching(self, mock_embed_text):
        mock_embed_text.side_effect = self._fake_embedding_for

        article = KnowledgeArticle.objects.create(
            title="Return Policy", category="returns", content="Returns info"
        )
        # Force it back to "not yet embedded" (bypassing the post_save
        # signal via a queryset update), simulating an article seeded
        # without triggering it -- e.g. via a data migration's
        # historical model, as the real seed migration does.
        KnowledgeArticle.objects.filter(pk=article.pk).update(embedding=None)

        knowledge_tools.search_knowledge_base("returns")

        article.refresh_from_db()
        self.assertIsNotNone(article.embedding)

    @patch("chatbot.services.embeddings.embed_text")
    def test_search_with_no_articles_returns_friendly_message(
        self, mock_embed_text
    ):
        result = knowledge_tools.search_knowledge_base("anything")
        self.assertEqual(result, "No knowledge base articles are available.")
        mock_embed_text.assert_not_called()


class EmbedTextTests(TestCase):
    @patch("chatbot.services.embeddings.genai")
    def test_embed_text_calls_embedding_model_and_returns_list(self, mock_genai):
        from chatbot.services.embeddings import EMBEDDING_MODEL, embed_text

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_client.models.embed_content.return_value.embeddings = [mock_embedding]

        result = embed_text("some article text")

        self.assertEqual(result, [0.1, 0.2, 0.3])
        mock_client.models.embed_content.assert_called_once_with(
            model=EMBEDDING_MODEL, contents="some article text"
        )
