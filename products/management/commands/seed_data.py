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

# ---------------------------------------------------------------------------
# Feature phrase banks, keyed by the exact item name used in CATEGORY_ITEMS.
# Descriptions are built by sampling from these instead of using random
# Faker lorem-ipsum text. This means every "Headphones" product shares real
# vocabulary with every other "Headphones" product ("noise cancellation",
# "40-hour battery life", etc.) while staying textually distinct from,
# say, "Yoga Mat" products. That shared vocabulary within an item type -
# and separation across item types - is exactly what TF-IDF / cosine
# similarity needs for content-based recommendations to work; random
# Faker paragraphs give the model nothing to key off of.
# ---------------------------------------------------------------------------
FEATURE_BANK = {
    "Headphones": ["over-ear design", "active noise cancellation", "40-hour battery life",
                   "Bluetooth 5.2 connectivity", "built-in microphone", "foldable design",
                   "plush memory-foam ear cushions"],
    "Bluetooth Speaker": ["360-degree sound", "IPX7 waterproof rating", "12-hour battery life",
                          "Bluetooth 5.0 pairing", "built-in speakerphone", "compact portable size"],
    "Smartwatch": ["heart rate monitor", "GPS tracking", "7-day battery life", "sleep tracking",
                   "water resistance up to 50m", "customizable watch faces"],
    "Laptop Stand": ["adjustable height", "aluminum alloy build", "foldable and portable",
                     "improved posture and airflow", "fits laptops up to 17 inches"],
    "Wireless Mouse": ["ergonomic design", "2.4GHz wireless connection", "adjustable DPI settings",
                       "silent click buttons", "long battery life"],
    "Mechanical Keyboard": ["tactile mechanical switches", "customizable RGB backlighting",
                            "durable aluminum frame", "detachable USB-C cable", "anti-ghosting keys"],
    "4K Monitor": ["Ultra HD 4K resolution", "HDR support", "narrow bezel design",
                   "adjustable stand", "multiple HDMI and DisplayPort inputs"],
    "Power Bank": ["20000mAh capacity", "fast charging support", "dual USB output ports",
                   "compact and lightweight", "built-in LED battery indicator"],
    "Action Camera": ["4K video recording", "waterproof up to 30m", "image stabilization",
                      "wide-angle lens", "Wi-Fi and Bluetooth connectivity"],
    "Noise-Cancelling Earbuds": ["active noise cancellation", "touch controls",
                                 "sweat and water resistance", "24-hour battery with charging case",
                                 "secure-fit ear tips"],
    "Router": ["dual-band Wi-Fi", "high-speed gigabit ports", "wide coverage range",
               "easy setup via mobile app", "parental control features"],
    "Webcam": ["1080p full HD resolution", "built-in noise-cancelling microphone",
               "auto light correction", "wide-angle lens", "plug-and-play USB connection"],

    "Cotton T-Shirt": ["100% breathable cotton", "relaxed fit", "reinforced stitching",
                       "machine washable", "available in multiple colors"],
    "Denim Jacket": ["classic denim wash", "button-front closure", "durable stitched seams",
                     "chest pockets", "versatile everyday layering"],
    "Running Shoes": ["lightweight cushioned sole", "breathable mesh upper",
                      "shock-absorbing midsole", "non-slip rubber outsole",
                      "designed for long-distance running"],
    "Wool Sweater": ["soft merino wool blend", "ribbed cuffs and hem", "warm winter layering",
                     "classic crew neckline", "machine washable wool"],
    "Slim-Fit Chinos": ["tailored slim fit", "stretch cotton fabric", "flat front design",
                        "versatile for work or casual wear", "machine washable"],
    "Rain Jacket": ["waterproof and windproof shell", "breathable fabric lining",
                    "adjustable hood", "packable and lightweight", "sealed seams"],
    "Leather Belt": ["genuine leather construction", "classic buckle design",
                     "durable stitched edges", "adjustable sizing",
                     "fits both casual and formal outfits"],
    "Baseball Cap": ["adjustable snapback closure", "breathable cotton fabric",
                     "curved brim for sun protection", "embroidered design",
                     "one-size-fits-most"],
    "Hoodie": ["soft fleece-lined interior", "adjustable drawstring hood",
               "kangaroo front pocket", "ribbed cuffs and hem", "relaxed everyday fit"],
    "Linen Shirt": ["lightweight breathable linen", "relaxed casual fit",
                    "button-front closure", "ideal for warm weather", "machine washable"],

    "Non-Stick Pan": ["durable non-stick coating", "even heat distribution",
                      "oven-safe up to 450°F", "ergonomic stay-cool handle",
                      "compatible with all stovetops"],
    "Electric Kettle": ["rapid boil technology", "1.7-liter capacity",
                        "auto shut-off feature", "cordless pour design", "BPA-free construction"],
    "Knife Set": ["high-carbon stainless steel blades", "ergonomic non-slip handles",
                  "includes wooden storage block", "razor-sharp precision edge",
                  "dishwasher safe"],
    "Blender": ["powerful 1000-watt motor", "multiple speed settings", "BPA-free pitcher",
                "stainless steel blades", "easy one-touch operation"],
    "Air Fryer": ["rapid hot-air circulation", "digital temperature control",
                  "non-stick dishwasher-safe basket", "reduces oil usage by up to 85%",
                  "compact countertop design"],
    "Cutting Board": ["durable bamboo construction", "juice groove to catch spills",
                      "knife-friendly surface", "easy to clean", "naturally antibacterial"],
    "Coffee Maker": ["programmable brew timer", "12-cup carafe capacity",
                     "auto shut-off feature", "reusable filter included",
                     "compact countertop footprint"],
    "Storage Jars": ["airtight silicone seal", "stackable space-saving design",
                     "clear glass for easy viewing", "BPA-free", "dishwasher safe"],
    "Bed Sheet Set": ["soft brushed microfiber", "deep pocket fitted sheet",
                      "wrinkle and fade resistance", "machine washable",
                      "hypoallergenic fabric"],
    "Table Lamp": ["adjustable brightness settings", "energy-efficient LED bulb",
                   "modern minimalist design", "touch-sensitive control",
                   "compact bedside footprint"],

    "Notebook Journal": ["thick cream lined pages", "durable hardcover binding",
                         "ribbon bookmark", "elastic closure band",
                         "compact travel-friendly size"],
    "Fiction Novel": ["gripping page-turning plot", "richly developed characters",
                      "critically acclaimed storytelling", "immersive narrative voice",
                      "great for book club discussion"],
    "Cookbook": ["easy-to-follow recipes", "step-by-step photography",
                 "covers everyday home cooking", "includes nutritional information",
                 "beginner-friendly instructions"],
    "Sketchbook": ["heavyweight acid-free paper", "spiral binding for easy flipping",
                   "smooth surface for pencil and ink", "compact portable size",
                   "durable cover"],
    "Self-Help Guide": ["practical actionable advice", "real-life case studies",
                        "step-by-step exercises", "focus on personal growth",
                        "written in an accessible tone"],
    "Children's Picture Book": ["colorful illustrations", "simple engaging story",
                                "designed for early readers", "durable board book pages",
                                "encourages imagination"],
    "Poetry Collection": ["evocative and lyrical verses", "explores themes of love and loss",
                          "beautifully written imagery", "compact collectible edition",
                          "perfect for quiet reflection"],

    "Yoga Mat": ["non-slip textured surface", "extra cushioning for joint support",
                 "lightweight and easy to carry", "eco-friendly TPE material",
                 "includes carrying strap"],
    "Dumbbell Set": ["adjustable weight plates", "durable rubber coating",
                     "ergonomic non-slip grip", "compact storage design",
                     "suitable for home workouts"],
    "Camping Tent": ["waterproof rainfly", "easy quick-pitch setup",
                     "spacious interior for multiple campers", "durable ripstop fabric",
                     "includes carry bag"],
    "Water Bottle": ["insulated double-wall stainless steel", "keeps drinks cold for 24 hours",
                     "leak-proof lid", "BPA-free construction", "lightweight and portable"],
    "Hiking Backpack": ["padded adjustable shoulder straps", "multiple storage compartments",
                        "water-resistant fabric", "breathable back panel",
                        "hydration bladder compatible"],
    "Resistance Bands": ["multiple resistance levels", "durable latex material",
                         "includes door anchor", "portable for home or travel workouts",
                         "ideal for strength training"],
    "Bicycle Helmet": ["lightweight aerodynamic shell", "adjustable ventilation system",
                       "impact-absorbing foam liner", "adjustable fit dial",
                       "reflective safety accents"],
    "Sleeping Bag": ["insulated for cold weather", "machine washable lining",
                     "compact compression sack included", "mummy-shaped design for warmth",
                     "durable water-resistant shell"],

    "Building Blocks Set": ["compatible with major building brick brands",
                            "encourages creative construction play",
                            "durable non-toxic plastic", "includes storage bag",
                            "suitable for ages 6 and up"],
    "Board Game": ["fun for the whole family", "quick to learn, easy to play",
                   "includes all pieces and instructions", "great for game night",
                   "supports 2-6 players"],
    "Puzzle": ["high-quality thick cardboard pieces", "vivid full-color printing",
               "challenging and engaging design", "great for family bonding",
               "includes reference poster"],
    "Remote Control Car": ["high-speed motor", "responsive remote control",
                           "rechargeable battery included", "durable shock-resistant frame",
                           "great for indoor and outdoor play"],
    "Plush Toy": ["ultra-soft huggable fabric", "child-safe stitched seams",
                  "machine washable", "cute collectible design",
                  "perfect for cuddling and gifting"],
    "Card Game": ["quick and easy to learn", "compact for travel",
                  "great for parties and family game night", "supports multiple players",
                  "includes rulebook"],

    "Face Moisturizer": ["deeply hydrating formula", "lightweight non-greasy texture",
                         "suitable for all skin types", "enriched with vitamin E",
                         "fragrance-free formula"],
    "Shampoo": ["gentle sulfate-free formula", "nourishes and strengthens hair",
                "suitable for daily use", "pleasant long-lasting scent",
                "safe for color-treated hair"],
    "Electric Toothbrush": ["oscillating cleaning technology", "multiple brushing modes",
                            "long-lasting rechargeable battery",
                            "built-in timer for even brushing", "gentle on gums"],
    "Perfume": ["long-lasting fragrance", "elegant glass bottle design",
                "notes of floral and citrus", "suitable for everyday wear",
                "travel-friendly size available"],
    "Hair Dryer": ["fast-drying airflow technology", "multiple heat and speed settings",
                   "lightweight ergonomic design", "reduces frizz and static",
                   "cool-shot button for styling"],
    "Lip Balm Set": ["deeply moisturizing formula", "made with natural ingredients",
                     "variety of flavors included", "travel-friendly packaging",
                     "soothes dry chapped lips"],

    "Organic Honey": ["100% pure and organic", "raw and unfiltered", "rich natural sweetness",
                      "sustainably sourced", "no added sugars or preservatives"],
    "Green Tea Pack": ["antioxidant-rich green tea leaves", "smooth mellow flavor",
                       "individually wrapped tea bags", "naturally caffeinated",
                       "sourced from organic tea gardens"],
    "Olive Oil": ["cold-pressed extra virgin", "rich robust flavor",
                  "sourced from Mediterranean olives", "great for cooking and dressings",
                  "non-GMO and additive-free"],
    "Roasted Coffee Beans": ["freshly roasted whole beans", "rich full-bodied flavor",
                             "sourced from single-origin farms", "medium roast profile",
                             "great for espresso or drip brewing"],
    "Trail Mix": ["blend of nuts, seeds, and dried fruit", "great source of energy",
                  "no artificial preservatives", "perfect for on-the-go snacking",
                  "resealable packaging"],
    "Pasta Set": ["made from durum wheat semolina", "authentic Italian recipe",
                  "cooks to a perfect al dente", "assorted pasta shapes included",
                  "non-GMO ingredients"],

    "Desk Organizer": ["multiple compartments for supplies", "durable mesh or wood construction",
                       "compact desktop footprint", "keeps workspace clutter-free",
                       "sturdy stackable design"],
    "Ballpoint Pen Set": ["smooth consistent ink flow", "comfortable ergonomic grip",
                          "quick-drying ink", "reliable everyday writing",
                          "includes multiple ink colors"],
    "Sticky Notes": ["strong repositionable adhesive", "bright assorted colors",
                     "compact size for notes and reminders", "acid-free paper",
                     "easy to write on"],
    "Desk Chair Cushion": ["memory foam support", "breathable mesh cover",
                           "reduces pressure while sitting", "non-slip base",
                           "machine washable cover"],
    "Whiteboard": ["smooth dry-erase surface", "includes mounting hardware",
                   "magnetic compatible surface", "easy to wipe clean",
                   "lightweight aluminum frame"],

    "Dog Leash": ["durable nylon webbing", "comfortable padded handle",
                  "reflective stitching for visibility", "adjustable length",
                  "sturdy metal clasp"],
    "Cat Scratching Post": ["natural sisal rope wrapping", "sturdy stable base",
                            "encourages healthy scratching habits",
                            "compact space-saving design", "soft plush platform"],
    "Pet Bed": ["ultra-soft cushioned interior", "machine washable cover",
                "non-slip bottom", "supportive bolster edges",
                "available in multiple sizes"],
    "Chew Toy": ["durable non-toxic rubber", "helps promote dental health",
                 "long-lasting for aggressive chewers", "textured surface for teeth cleaning",
                 "safe for daily play"],
    "Pet Food Bowl": ["non-slip rubber base", "stainless steel construction",
                      "easy to clean", "dishwasher safe", "durable and rust-resistant"],
}

CATEGORY_CLOSERS = {
    "Electronics": ["reliable performance for everyday tech needs",
                    "a smart addition to your gadget collection",
                    "great value for tech enthusiasts"],
    "Clothing": ["comfortable everyday wear", "a versatile addition to your wardrobe",
                 "great for any season"],
    "Home & Kitchen": ["making everyday cooking and living easier",
                       "a practical upgrade for your home",
                       "great value for your kitchen"],
    "Books": ["a great addition to any reading list", "perfect for quiet time at home",
              "an engaging read for all ages"],
    "Sports & Outdoors": ["supporting an active lifestyle",
                          "great for your next outdoor adventure",
                          "built for consistent training"],
    "Toys & Games": ["hours of fun for the whole family",
                     "a great gift for kids of all ages",
                     "perfect for family game nights"],
    "Beauty & Personal Care": ["part of a healthy daily routine",
                               "gentle care for everyday use",
                               "a must-have self-care essential"],
    "Grocery": ["a wholesome addition to your pantry",
                "great for everyday meals and snacking",
                "sourced with quality in mind"],
    "Office Supplies": ["keeping your workspace organized and efficient",
                        "a practical essential for work or study",
                        "built for everyday office use"],
    "Pet Supplies": ["keeping your furry friend happy and healthy",
                     "a thoughtful addition to your pet's routine",
                     "built to last through daily use"],
}


def build_product_content(base_item, collection_title):
    """
    Builds (description, title_feature) using real, item-specific feature
    phrases instead of random lorem-ipsum text.

    - description: pulls 2-3 feature phrases from FEATURE_BANK[base_item],
      so every product of the same type shares real vocabulary with every
      other product of that type, while staying distinct from other types.
    - title_feature: one additional feature phrase, chosen so it does NOT
      repeat anything already used in the description. This gets appended
      to the product title, so title and description reinforce the same
      product-type signal (both draw from the same bank) without being
      literally identical text.

    """
    features = FEATURE_BANK.get(base_item, [])
    closer = random.choice(
        CATEGORY_CLOSERS.get(collection_title, ["reliable everyday quality"])
    )

    if features:
        chosen = random.sample(features, k=min(3, len(features)))
        if len(chosen) > 1:
            feature_text = ", ".join(chosen[:-1]) + " and " + chosen[-1]
        else:
            feature_text = chosen[0]
        description = f"This {base_item.lower()} offers {feature_text}. Designed for {closer}."

        remaining = [f for f in features if f not in chosen]
        title_feature = random.choice(remaining) if remaining else random.choice(features)
    else:
        description = f"A dependable {base_item.lower()} designed for {closer}."
        title_feature = None

    return description, title_feature

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

        # deleting the ProductImage row does NOT delete the actual file
        # on disk - Django never does that automatically - so each
        # file has to be removed explicitly first, or every --clear run
        # leaves orphaned image files behind in MEDIA_ROOT
        for product_image in ProductImage.objects.all():
            product_image.image.delete(save=False)
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

            description, title_feature = build_product_content(base_item, collection.title)

            title = f"{random.choice(ADJECTIVES)} {base_item}"
            if title_feature:
                # capitalize only the first character - str.capitalize()
                # would lowercase mid-phrase words like "Bluetooth"
                title_feature_display = title_feature[0].upper() + title_feature[1:]
                title = f"{title} - {title_feature_display}"

            product = Product.objects.create(
                title=title,
                description=description,
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
        signal Djoser triggers).
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
