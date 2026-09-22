# Store — E-commerce Backend

## 1. Project Overview

This is a Django + Django REST Framework backend for an e-commerce store. It is organized into five Django apps plus the project package:

- **`store/`** — the Django project package (settings, root URLconf, WSGI/ASGI entry points, Celery bootstrap). Contains no models or views of its own.
- **`products/`** — the core commerce domain: products, collections, product images, customers, carts, orders, order items, reviews, and addresses. Also hosts an AI-powered review-summary service (Google Gemini) and a `seed_data` management command for generating demo data.
- **`users/`** — a thin layer on top of Django's built-in `auth.User` model, providing Djoser-compatible serializers for registration and profile data. There is no custom user model.
- **`tags/`** — a generic tagging system (via `GenericForeignKey`/`ContentType`), currently wired up only for tagging products.
- **`recommendations/`** — a product recommendation engine with two algorithms: content-based filtering (TF-IDF + cosine similarity over product text) and collaborative filtering (customer–product interaction matrix + cosine similarity), plus a Celery task to regenerate both.
- **`chatbot/`** — an AI shopping-assistant chatbot built with LangChain + Google Gemini. It uses a tool-calling agent that can search products, check reviews, fetch recommendations, manage the authenticated customer's cart, and look up their orders, plus a small RAG-style knowledge base (FAQ articles with vector embeddings) for shipping/returns/payment questions.

It is designed to be consumed by a separate frontend SPA (a sibling `store-frontend` project), with CORS defaulting to `http://localhost:5173`.

## 2. Features

- Product catalog with collections, images, filtering, search, and pagination
- Shopping cart and order placement with atomic stock validation and inventory decrement
- Customer accounts with profile data, membership tiers (Bronze/Silver/Gold), and a single shipping address
- Product reviews (one per customer per product) with AI-generated review summaries (Gemini), cached in Redis
- Product tagging (generic, reusable tagging system)
- Product recommendations: "similar products" (content-based) and personalized picks (collaborative filtering)
- AI shopping-assistant chatbot with tool-calling (cart management, product/review/recommendation lookups, order lookups) and a knowledge-base FAQ with streaming responses
- JWT-based authentication and registration/activation via Djoser
- Async task processing via Celery (recommendation regeneration) with Celery Beat for scheduling
- Optional S3-compatible (Supabase Storage) media storage for production

## 3. Tech Stack

| Concern | Library | Version (locked) |
|---|---|---|
| Web framework | Django | 6.0.8 |
| API framework | Django REST Framework | 3.18.1 |
| Filtering | django-filter | 26.1 |
| Nested routers | drf-nested-routers | 0.95.3 |
| Auth/registration | Djoser | 2.3.4 |
| JWT | djangorestframework-simplejwt | 5.5.1 |
| Image handling | Pillow | 12.3.0 |
| ML / recommendations | pandas, scikit-learn, numpy | 3.0.5 / 1.9.0 / 2.5.3 |
| Async tasks | Celery, django-celery-beat, redis | 5.6.3 / 2.9.0 / 8.1.0 |
| CORS | django-cors-headers | 4.9.0 |
| AI / LLM | google-genai, langchain-google-genai, langchain | 2.22.0 / 4.4.0 / 1.4.0 |
| Env config | python-dotenv | 1.2.3 |
| WSGI server | gunicorn | 26.2.0 |
| Static files | whitenoise | 6.12.0 |
| Object storage | django-storages[s3] | 1.14.6 |
| DB drivers | mysqlclient (MySQL), psycopg[binary] (PostgreSQL) | 2.2.8 / 3.3.5 |
| Dev-only | Faker (used by `seed_data`) | — |

Python version: **3.13** (pinned in `Pipfile`). Dependency management: **Pipenv** (`Pipfile` / `Pipfile.lock`).

## 4. Architecture

The root URLconf (`store/urls.py`) wires the apps together:

```python
path('admin/', admin.site.urls)
path('', include('products.urls'))
path('auth/', include('djoser.urls'))
path('auth/', include('djoser.urls.jwt'))
path('', include('recommendations.urls'))
path('', include('tags.urls'))
path('chat/', include('chatbot.urls'))
```

The Django admin site is rebranded "Abd Store". Media files are served by the Django dev server only when `DEBUG=True`.

Each domain app follows a consistent layout: `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `apps.py`. `products` and `chatbot` additionally have a `services/` package that isolates business logic (Gemini calls, recommendation prompts, the chatbot agent) from the view layer, and `products` has dedicated `permissions.py`, `filters.py`, `pagination.py`, and `signals.py` modules.

Routing uses `rest_framework_nested.routers` (`DefaultRouter` + `NestedDefaultRouter`) in `products/urls.py` and `tags/urls.py` to auto-generate CRUD endpoints from viewsets and nest product-scoped resources (images, reviews, review summaries, tags) under `/products/{id}/...`. `recommendations` and `chatbot` use plain `path()` routes with class-based views instead.

Cross-model side effects are handled via Django signals, registered in each app's `apps.py::ready()`:
- `products/signals.py` — auto-creates a `Customer` when a `User` is created, and auto-creates a `Cart` when that `Customer` is created.
- `chatbot/signals.py` — computes and stores a vector embedding on a `KnowledgeArticle` whenever it's saved (skipped for fixture/raw saves).

Celery (`store/celery.py`) bootstraps an app named `store`, configured from Django settings and auto-discovering tasks (currently `recommendations/tasks.py`).

> **Note:** `products/urls.py` and `tags/urls.py` both independently register a top-level `products` route bound to the same `ProductViewSet`. Since both are mounted at `''` in the root URLconf, they compose without conflict, but this is a duplicated registration worth being aware of.

## 5. Database Models

### `products` app
- **Collection** — `title` (CharField); `featured_product` (FK → Product, `SET_NULL`, nullable).
- **Product** — `title` (CharField), `description` (TextField, nullable), `price` (Decimal 6,2, min 1), `inventory` (Integer, min 0), `last_update` (auto), `collection` (FK → Collection, `PROTECT`).
- **ProductImage** — `product` (FK → Product, `CASCADE`), `image` (ImageField).
- **Customer** — `phone`, `birth_date` (nullable), `membership` (choice: Bronze/Silver/Gold, default Bronze), `user` (OneToOne → `auth.User`, `CASCADE`), `profile_image` (ImageField, nullable). Exposes `first_name()`/`last_name()` proxy methods for the admin.
- **Order** — `placed_at` (auto), `payment_status` (choice: Pending/Complete/Failed, default Pending), `customer` (FK → Customer, `PROTECT`).
- **OrderItem** — `order` (FK → Order, `PROTECT`), `product` (FK → Product, `PROTECT`), `quantity`, `unit_price` (snapshotted at order time).
- **Address** — `street`, `city`, `customer` (OneToOne → Customer, `CASCADE`) — one address per customer.
- **Cart** — `id` (UUID primary key), `customer` (OneToOne → Customer, `CASCADE`), `created_at` (auto).
- **CartItem** — `cart` (FK → Cart, `CASCADE`), `product` (FK → Product, `CASCADE`), `quantity` (min 1); unique per (cart, product).
- **Review** — `product` (FK, `CASCADE`), `customer` (FK, `CASCADE`), `rating` (1–5), `comment`, `created_at` (auto); unique per (product, customer).

### `users` app
No models defined — the app uses Django's default `auth.User` model directly (`AUTH_USER_MODEL` is not overridden).

### `tags` app
- **Tag** — `label` (CharField).
- **TaggedItem** — `tag` (FK → Tag, `CASCADE`), `content_type` (FK → ContentType), `object_id`, `content_object` (`GenericForeignKey`) — a generic tagging relation usable against any model, currently applied to `Product`.

### `recommendations` app
- **ProductRecommendation** — `product` (FK → Product), `recommended_product` (FK → Product), `score` (Float). Item-to-item similarity from the content-based algorithm.
- **UserRecommendation** — `customer` (FK → Customer), `product` (FK → Product), `score` (Float). Personalized picks from collaborative filtering.

### `chatbot` app
- **Conversation** — `customer` (OneToOne → `products.Customer`, `CASCADE`), `created_at`/`updated_at` (auto). One thread per customer.
- **Message** — `conversation` (FK → Conversation, `CASCADE`), `role` (choice: user/assistant), `content` (TextField), `created_at` (auto).
- **KnowledgeArticle** — `title`, `category` (choice: shipping/returns/payment/faq/general), `content`, `embedding` (JSONField, not editable — stores the Gemini embedding vector), `created_at`/`updated_at` (auto).

## 6. API Endpoints

### Products (`products/urls.py`, mounted at `/`)
| Method(s) | Path | Description |
|---|---|---|
| GET, POST, PATCH, DELETE | `/products/`, `/products/{id}/` | Product CRUD. Public read; staff-only write. Filterable (collection, price range), searchable (title/description), orderable, paginated (12/page, max 100). |
| GET, POST, PATCH, DELETE | `/collections/`, `/collections/{id}/` | Collection CRUD. Public read; staff-only write. |
| GET, POST, PATCH, DELETE | `/admin-collections/` | Staff-only collection management with product counts and featured-product details. |
| GET | `/cart/` | The authenticated user's own cart. |
| GET, POST, PATCH, DELETE | `/cart-items/` | Manage items in the caller's own cart. |
| GET, PUT, PATCH, DELETE | `/customers/` | Staff-only customer management. |
| GET, PUT, PATCH | `/customers/me/` | The logged-in user's own customer profile. |
| GET, POST, PATCH, DELETE | `/orders/`, `/orders/{id}/` | Order history/creation. Customers see only their own; staff can update/delete any. Creating an order builds it from the cart (atomic: validates stock, decrements inventory, snapshots prices, clears cart). |
| GET, POST, PUT, DELETE | `/addresses/` | The caller's own address (max one, enforced server-side). |
| GET, POST, DELETE | `/products/{product_id}/images/` | Product image management. Staff-only write. |
| GET, POST, PATCH, DELETE | `/products/{product_id}/reviews/` | Product reviews. Authenticated create; only the review's author can update/delete. |
| GET | `/products/{product_id}/summary/` | AI-generated review summary (Gemini), cached in Redis. |

### Auth (Djoser, mounted at `/auth/`)
| Method | Path | Description |
|---|---|---|
| POST | `/auth/users/` | Register a new user. |
| GET, PUT, PATCH, DELETE | `/auth/users/me/` | Manage the current user account. |
| POST | `/auth/users/activation/` | Activate an account via emailed uid/token. |
| POST | `/auth/users/resend_activation/` | Resend the activation email. |
| POST | `/auth/users/reset_password/` (+ related) | Password reset flow (standard Djoser endpoints). |
| POST | `/auth/jwt/create/` | Obtain JWT access/refresh tokens (login). |
| POST | `/auth/jwt/refresh/` | Refresh an access token. |
| POST | `/auth/jwt/verify/` | Verify a token. |

### Recommendations (`recommendations/urls.py`, mounted at `/`)
| Method | Path | Description |
|---|---|---|
| GET | `/products/{product_id}/similar/` | "Similar products" (content-based). Generated lazily on first request if none exist yet. |
| GET | `/recommendations/` | Personalized recommendations for the authenticated customer (collaborative filtering), generated lazily. |

### Tags (`tags/urls.py`, mounted at `/`)
| Method | Path | Description |
|---|---|---|
| GET, POST, DELETE | `/products/{product_id}/tags/` | List/attach/remove tags on a product. Read is open; create/destroy require staff. |

### Chatbot (`chatbot/urls.py`, mounted at `/chat/`)
| Method | Path | Description |
|---|---|---|
| GET | `/chat/` | The authenticated customer's conversation history. |
| POST | `/chat/` | Send a message; runs the tool-calling agent and returns the full assistant reply. |
| POST | `/chat/stream/` | Same as above, but streams the assistant's reply chunk by chunk (`text/plain` streaming response). |

## 7. Authentication

- **Mechanism**: Stateless JWT via `djangorestframework-simplejwt`, integrated through **Djoser**. `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` is set exclusively to `JWTAuthentication` — no session or basic auth for the API.
- **Header format**: `SIMPLE_JWT['AUTH_HEADER_TYPES'] = ('JWT',)`, so clients must send `Authorization: JWT <access_token>` (not the SimpleJWT default `Bearer`).
- **User model**: Django's default `auth.User` (no custom user model). Store-specific profile data lives on a separate `products.Customer` model (`OneToOneField` to `User`), auto-created via a signal whenever a `User` is created, which in turn auto-creates a `Cart`.
- **Registration & activation**: Handled by Djoser — password retype required at signup, activation email sent via Gmail SMTP, activation URL pattern `activate/{uid}/{token}` (matching the frontend's `/activate/:uid/:token` route). Custom serializers (`users/serializers.py`) extend Djoser's defaults to add `first_name`/`last_name`/`username`, enforce unique case-insensitive email, and expose `is_staff`.
- **Permissions**: Standard DRF classes (`IsAuthenticated`, `IsAdminUser`, `IsAuthenticatedOrReadOnly`, `AllowAny`) plus two custom classes in `products/permissions.py`: `IsAdminOrReadOnly` (safe methods open, writes require staff) and `IsReviewOwner` (object-level check that the review belongs to the requesting user). Most viewsets additionally scope querysets to the requesting user's own data in `get_queryset`.

## 8. Environment Variables

All variables are loaded from `.env` via `python-dotenv` and read with `os.getenv(...)` in `store/settings.py`. See `.env.example` for the template.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key. Must be a real generated value when `DEBUG=False` (the app refuses to boot otherwise). |
| `DEBUG` | Toggles Django debug mode. |
| `ALLOWED_HOSTS` | Comma-separated hostnames; only read when `DEBUG=False`. |
| `DB_ENGINE` | `mysql` (local dev default) or `postgresql` (production). |
| `NAME`, `HOST`, `USER`, `PASSWORD` | Database connection credentials. |
| `DB_PORT` | Database port (blank = engine default). |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Gmail SMTP credentials for Djoser activation emails. |
| `EMAIL_FRONTEND_PROTOCOL`, `EMAIL_FRONTEND_DOMAIN`, `EMAIL_FRONTEND_SITE_NAME` | Used by Djoser to build activation links pointing at the separate frontend app. |
| `GEMINI_API_KEY` | Google Gemini API key, used for AI review summaries and the chatbot. |
| `REVIEW_SUMMARY_CACHE_TTL` | Seconds to cache an AI-generated review summary (default 3600). |
| `REDIS_URL` | Redis connection string; used as the Django cache backend and default Celery broker/result backend (default `redis://localhost:6379/0`, required — no in-memory fallback). |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Optional overrides if Celery should use a different Redis instance than the cache. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed frontend origin(s); defaults to `http://localhost:5173`. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins for CSRF (needed behind a proxy/custom domain). |
| `USE_S3_MEDIA` | Switches media storage from local filesystem to an S3-compatible bucket. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME` | Supabase Storage (S3-compatible) bucket credentials/endpoint, only used when `USE_S3_MEDIA=True`. |

## 9. Local Setup

> These steps are inferred from `Pipfile`, `manage.py`, and `settings.py`; there is no setup script in the repository.

1. Install **Python 3.13** and **Pipenv**, then install dependencies:
   ```bash
   pipenv install
   ```
2. Copy the environment template and fill in real values:
   ```bash
   cp .env.example .env
   ```
3. Provide a running database matching `DB_ENGINE` (MySQL is the local-dev default in `.env.example`; PostgreSQL is used in production). There is no SQLite fallback configured — the `db.sqlite3` file present in the repo is a stray, unused artifact.
4. Provide a running **Redis** instance (`REDIS_URL`) — required for the cache backend and Celery; there is no in-memory fallback.
5. Apply migrations:
   ```bash
   pipenv run python manage.py migrate
   ```
6. Create an admin user:
   ```bash
   pipenv run python manage.py createsuperuser
   ```
7. *(Optional)* Seed demo data:
   ```bash
   pipenv run python manage.py seed_data
   ```
8. Start the dev server:
   ```bash
   pipenv run python manage.py runserver
   ```
9. *(Optional, for recommendations/chat background work)* Start a Celery worker and beat process:
   ```bash
   pipenv run celery -A store worker
   pipenv run celery -A store beat
   ```
10. Set `GEMINI_API_KEY` to enable the AI review-summary and chatbot features — without it those specific code paths will fail, but the rest of the app functions normally.

## 10. Deployment

**No deployment manifest exists in this repository** — there is no `Procfile`, `Dockerfile`, `docker-compose.yml`, `runtime.txt`, or CI/CD configuration. The following is what the dependencies and settings *imply* about the intended production setup, not a documented deployment procedure:

- `gunicorn` and `whitenoise` are declared dependencies, and `WhiteNoiseMiddleware` is registered — suggesting Gunicorn serves the app (`store.wsgi:application`) with WhiteNoise handling static files.
- `django-storages[s3]` plus the `USE_S3_MEDIA`/`AWS_*` settings indicate production media is intended to be served from a Supabase Storage S3-compatible bucket rather than local disk.
- `settings.py` includes production-hardening settings gated on `DEBUG=False` (SSL redirect, secure cookies, HSTS with a 1-week max-age), with a comment noting it "assumes a standard reverse-proxy/PaaS setup that terminates TLS" — implying a PaaS-style host (e.g. Render, Railway), though no specific platform config is present.
- Python version is pinned only via `Pipfile`'s `[requires] python_version = "3.13"` (no `runtime.txt`).

If you deploy this project, you'll need to write your own Procfile/Dockerfile/CI config — none is provided.

## 11. Folder Structure

```
store/
├── .env.example              # Environment variable template
├── manage.py                  # Django management entrypoint
├── Pipfile / Pipfile.lock     # Pipenv dependency manifest + lock
├── chatbot/
│   ├── models.py               # Conversation, Message, KnowledgeArticle
│   ├── serializers.py
│   ├── views.py                # ChatView, ChatStreamView
│   ├── urls.py
│   ├── signals.py              # auto-embeds KnowledgeArticle on save
│   └── services/
│       ├── agent.py             # ChatAgent (LangChain tool-calling loop)
│       ├── llm.py                # ChatGoogleGenerativeAI factory
│       ├── embeddings.py         # Gemini embedding helper
│       ├── prompt.py             # System prompt
│       └── tools/                # cart, orders, products, recommendations, reviews, knowledge
├── products/
│   ├── models.py                # Collection, Product, ProductImage, Customer,
│   │                             # Order, OrderItem, Address, Cart, CartItem, Review
│   ├── serializers.py
│   ├── views.py                 # ModelViewSets + ReviewSummaryViewSet
│   ├── urls.py                  # DRF router + nested routers
│   ├── permissions.py           # IsAdminOrReadOnly, IsReviewOwner
│   ├── filters.py                # ProductFilter
│   ├── pagination.py             # ProductPagination
│   ├── signals.py                # auto-create Customer/Cart
│   ├── services/
│   │   ├── gemini_client.py       # GeminiClient / GeminiServiceError
│   │   └── prompt.py               # Review-summary prompt builder
│   └── management/commands/
│       └── seed_data.py            # Faker-based demo data seeder
├── recommendations/
│   ├── models.py                  # ProductRecommendation, UserRecommendation
│   ├── views.py                   # SimilarProductsView, UserRecommendationView
│   ├── urls.py
│   ├── tasks.py                   # Celery task: generate_recommendations
│   └── services/
│       ├── content_based.py        # TF-IDF + cosine similarity
│       └── collaborative.py        # interaction matrix + cosine similarity
├── tags/
│   ├── models.py                   # Tag, TaggedItem (generic FK)
│   ├── views.py                    # ProductTagViewSet
│   └── urls.py
├── users/
│   ├── models.py                   # empty — uses default auth.User
│   └── serializers.py              # Djoser-derived UserCreateSerializer, UserSerializer
└── store/                          # Django project package
    ├── settings.py
    ├── urls.py                      # root URLconf
    ├── celery.py                    # Celery app bootstrap
    ├── wsgi.py
    └── asgi.py
```

(`__pycache__/`, `migrations/`, `staticfiles/`, `media/`, `.git/`, `.idea/`, `.vscode/` omitted for clarity.)
