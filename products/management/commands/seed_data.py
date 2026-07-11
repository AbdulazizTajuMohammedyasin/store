"""
Management command to populate the store app with realistic dummy data.

Place this file at:  <your_app>/management/commands/seed_data.py
(create empty __init__.py files in `management/` and `management/commands/`
if they don't already exist)

Run with:
    python manage.py seed_data
    python manage.py seed_data --clear      # wipes existing data first
    python manage.py seed_data --products 200 --customers 100

Requires:
    pip install faker Pillow
"""
import io
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from faker import Faker

# vvv change this import to match your app's actual name vvv
from products.models import (
    Address, Cart, CartItem, Collection, Customer, Order, OrderItem,
    Product, ProductImage, Review,
)

fake = Faker()
User = get_user_model()

# ---------------------------------------------------------------------------
# Reference data used to build believable, non-repetitive product names
# ---------------------------------------------------------------------------
CATEGORY_ITEMS = {
    "Electronics": ["Headphones", "Bluetooth Speaker", "Smartwatch", "Laptop Stand",
                    "Wireless Mouse", "Mechanical Keyboard", "4K Monitor", "Power Bank",
                    "Action Camera", "Noise-Cancelling Earbuds", "Router", "Webcam"],
    "Clothing": ["Cotton T-Shirt", "Denim Jacket", "Running Shoes", "Wool Sweater",
                 "Slim-Fit Chinos", "Rain Jacket", "Leather Belt", "Baseball Cap",
                 "Hoodie", "Linen Shirt"],
    "Home & Kitchen": ["Non-Stick Pan", "Electric Kettle", "Knife Set", "Blender",
                       "Air Fryer", "Cutting Board", "Coffee Maker", "Storage Jars",
                       "Bed Sheet Set", "Table Lamp"],
    "Books": ["Notebook Journal", "Fiction Novel", "Cookbook", "Sketchbook",
              "Self-Help Guide", "Children's Picture Book", "Poetry Collection"],
    "Sports & Outdoors": ["Yoga Mat", "Dumbbell Set", "Camping Tent", "Water Bottle",
                          "Hiking Backpack", "Resistance Bands", "Bicycle Helmet",
                          "Sleeping Bag"],
    "Toys & Games": ["Building Blocks Set", "Board Game", "Puzzle", "Remote Control Car",
                     "Plush Toy", "Card Game"],
    "Beauty & Personal Care": ["Face Moisturizer", "Shampoo", "Electric Toothbrush",
                               "Perfume", "Hair Dryer", "Lip Balm Set"],
    "Grocery": ["Organic Honey", "Green Tea Pack", "Olive Oil", "Roasted Coffee Beans",
                "Trail Mix", "Pasta Set"],
    "Office Supplies": ["Desk Organizer", "Ballpoint Pen Set", "Sticky Notes",
                        "Desk Chair Cushion", "Whiteboard"],
    "Pet Supplies": ["Dog Leash", "Cat Scratching Post", "Pet Bed", "Chew Toy",
                     "Pet Food Bowl"],
}

ADJECTIVES = ["Premium", "Classic", "Deluxe", "Portable", "Wireless", "Smart",
              "Eco-Friendly", "Compact", "Professional", "Ultra", "Everyday",
              "Heavy-Duty", "Modern", "Essential"]

REVIEW_COMMENTS = [
    "Works exactly as described, very happy with this purchase.",
    "Good value for the price, would buy again.",
    "Quality is decent but delivery took longer than expected.",
    "Exceeded my expectations, highly recommend!",
    "It's okay, nothing special but does the job.",
    "Broke after a few weeks of light use, disappointed.",
    "Great build quality and looks even better in person.",
    "Customer service was helpful when I had an issue.",
]


class Command(BaseCommand):
    help = "Seeds the database with realistic fake data for development/testing."

    def add_arguments(self, parser):
        parser.add_argument("--products", type=int, default=100)
        parser.add_argument("--customers", type=int, default=60)
        parser.add_argument("--orders", type=int, default=80)
        parser.add_argument("--clear", action="store_true",
                             help="Delete existing seeded data before creating new data.")

    def handle(self, *args, **options):
        if options["clear"]:
            self.clear_data()

        with transaction.atomic():
            collections = self.create_collections()
            products = self.create_products(collections, options["products"])
            self.create_product_images(products)
            customers = self.create_customers(options["customers"])
            self.create_carts_and_cart_items(customers, products)
            self.create_orders(customers, products, options["orders"])
            self.create_reviews(customers, products)

        self.stdout.write(self.style.SUCCESS("Database seeding complete."))

    # ------------------------------------------------------------------
    def clear_data(self):
        self.stdout.write("Clearing existing data...")
        Review.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        CartItem.objects.all().delete()
        Cart.objects.all().delete()
        ProductImage.objects.all().delete()
        Product.objects.all().delete()
        Collection.objects.all().delete()
        Address.objects.all().delete()
        Customer.objects.all().delete()
        User.objects.filter(is_superuser=False, is_staff=False).delete()

    # ------------------------------------------------------------------
    def create_collections(self):
        self.stdout.write("Creating collections...")
        collections = []
        for title in CATEGORY_ITEMS.keys():
            collection, _ = Collection.objects.get_or_create(title=title)
            collections.append(collection)
        return collections

    # ------------------------------------------------------------------
    def create_products(self, collections, count):
        """
        Uses Product.objects.create() in a loop instead of bulk_create().

        bulk_create() does not reliably populate the primary key on the
        Python objects it returns - on Postgres it does (via RETURNING),
        but on MySQL and older SQLite versions the returned objects come
        back with pk=None. Every downstream use of these products as a
        ForeignKey (ProductImage, Collection.featured_product, CartItem,
        OrderItem, Review) then fails with:
            ValueError: save() prohibited to prevent data loss due to
            unsaved related object
        because Django sees pk=None and treats the object as unsaved.

        For a few hundred rows the performance difference vs bulk_create
        is negligible, so plain create() is used here - it always
        returns a fully-saved instance with a real pk, which removes
        this whole class of bug.
        """
        self.stdout.write(f"Creating {count} products...")
        created = []
        for _ in range(count):
            collection = random.choice(collections)
            base_item = random.choice(CATEGORY_ITEMS[collection.title])
            title = f"{random.choice(ADJECTIVES)} {base_item}"

            product = Product.objects.create(
                title=title,
                description=fake.paragraph(nb_sentences=4),
                price=Decimal(random.randrange(500, 50000)) / 100,  # 5.00 - 500.00
                inventory=random.randint(0, 300),
                collection=collection,
            )
            created.append(product)

        # assign each collection a featured_product now that products
        # with real, saved pks exist
        for collection in collections:
            candidates = [p for p in created if p.collection_id == collection.id]
            if candidates:
                collection.featured_product = random.choice(candidates)
                collection.save()

        return created

    # ------------------------------------------------------------------
    def create_product_images(self, products):
        """
        Attaches 1-2 tiny generated placeholder images to about half the
        products, so ProductImage rows have real files behind them.
        Requires Pillow. If Pillow isn't installed this step is skipped.
        """
        try:
            from PIL import Image
        except ImportError:
            self.stdout.write(self.style.WARNING(
                "Pillow not installed - skipping product image generation "
                "(pip install Pillow to enable)."
            ))
            return

        self.stdout.write("Creating placeholder product images...")
        sample = random.sample(products, k=len(products) // 2)
        for product in sample:
            for i in range(random.randint(1, 2)):
                color = tuple(random.randint(0, 255) for _ in range(3))
                img = Image.new("RGB", (400, 400), color=color)
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                ProductImage.objects.create(
                    product=product,
                    image=ContentFile(
                        buffer.getvalue(),
                        name=f"product_{product.id}_{i}.png",
                    ),
                )

    # ------------------------------------------------------------------
    def create_customers(self, count):
        """
        Creates real auth Users the same way Djoser's registration
        endpoint would (via create_user, which fires the same post_save
        signal Djoser triggers). Your signals then auto-create the
        Customer, and the Customer's own post_save signal auto-creates
        the Cart - so we never call Customer.objects.create(...) or
        Cart.objects.create(...) ourselves. We just fetch what the
        signals already made and fill in the extra fields.
        """
        self.stdout.write(f"Creating {count} customers...")
        customers = []
        membership_weights = ["B"] * 6 + ["S"] * 3 + ["G"] * 1  # mostly Bronze

        for _ in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = fake.unique.user_name()
            email = fake.unique.email()

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password="testpass123",
            )

            # the signal has already created the Customer row by this
            # point (post_save fires synchronously) - fetch it rather
            # than creating a new one
            customer = Customer.objects.get(user=user)
            customer.phone = fake.msisdn()[:15]
            customer.birth_date = fake.date_of_birth(minimum_age=18, maximum_age=75)
            customer.membership = random.choice(membership_weights)
            customer.save()
            customers.append(customer)

            # ~70% of customers get a saved address
            if random.random() < 0.7:
                Address.objects.create(
                    customer=customer,
                    street=fake.street_address(),
                    city=fake.city(),
                )

            # cart already exists via your Customer -> Cart signal;
            # nothing to create here

        return customers

    # ------------------------------------------------------------------
    def create_carts_and_cart_items(self, customers, products):
        self.stdout.write("Adding items to some active carts...")
        # about half of customers currently have something sitting in their cart
        shopping_customers = random.sample(customers, k=len(customers) // 2)
        for customer in shopping_customers:
            cart = customer.cart
            chosen_products = random.sample(products, k=random.randint(1, 5))
            for product in chosen_products:
                CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=random.randint(1, 3),
                )

    # ------------------------------------------------------------------
    def create_orders(self, customers, products, count):
        self.stdout.write(f"Creating {count} orders...")
        status_weights = ["C"] * 6 + ["P"] * 3 + ["F"] * 1  # mostly complete

        for _ in range(count):
            customer = random.choice(customers)
            order = Order.objects.create(
                customer=customer,
                payment_status=random.choice(status_weights),
            )
            order_products = random.sample(products, k=random.randint(1, 4))
            for product in order_products:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=random.randint(1, 3),
                    unit_price=product.price,  # price captured at time of order
                )

    # ------------------------------------------------------------------
    def create_reviews(self, customers, products):
        self.stdout.write("Creating reviews...")
        # each review needs a unique (product, customer) pair, so build
        # random pairs and skip any duplicates instead of forcing a count
        target_review_count = int(len(products) * 1.5)
        created = 0
        attempts = 0
        seen_pairs = set()

        while created < target_review_count and attempts < target_review_count * 5:
            attempts += 1
            product = random.choice(products)
            customer = random.choice(customers)
            pair = (product.id, customer.id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            Review.objects.create(
                product=product,
                customer=customer,
                rating=random.randint(1, 5),
                comment=random.choice(REVIEW_COMMENTS),
            )
            created += 1
