# Book Store API

A JSON API for a small book catalogue, built with Django and Django REST Framework.
It grew out of a server-rendered Django book store (see the `book_store` repo) and
exposes the same data as an API for a separate frontend (see `book_store_frontend`).

## What it does

- Lists, creates, updates and deletes **books** and **authors**
- Books carry their author and the countries they are published in
- **Search** (`?search=`), **filter** (`?bestselling=true`) and **sort** (`?ordering=title`, `-rating`)
- **Pagination**, 10 per page (`?page=2`)
- **Token login**: anyone can read; changing data needs a token
- Related data is fetched with `select_related` / `prefetch_related` (3 queries per page instead of 32)
- Interactive API docs generated from the code (OpenAPI / Swagger UI)
- 23 automated tests, including a test that pins the JSON shape of a book

## Endpoints

| Method | URL | Notes |
|---|---|---|
| POST | `/api/token/` | Send `username` and `password`, get a token back |
| GET, POST | `/api/books/` | List (paginated) or create. Create needs a token |
| GET, PUT, PATCH, DELETE | `/api/books/<id>/` | Change and delete need a token |
| GET, POST | `/api/authors/` | Same pattern as books |
| GET | `/api/docs/` | Swagger UI |
| GET | `/api/schema/` | The OpenAPI file |

Send the token as a header: `Authorization: Token <your token>`.

## Run it

```bash
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8001
```

Then open http://127.0.0.1:8001/api/docs/.

## Run the tests

```bash
python manage.py test
```

## Notes

- Uses SQLite locally. The database file is not committed.
- `CORS_ALLOWED_ORIGINS` in `book_store/settings.py` lists the addresses the
  frontend page may run on (`127.0.0.1:8002` by default).
