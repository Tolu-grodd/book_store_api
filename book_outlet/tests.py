from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Author, Book, Country


class BookApiTests(APITestCase):
    # setUp runs before every test; each test gets a fresh, empty test database
    def setUp(self):
        self.author = Author.objects.create(first_name="J.R.R.", last_name="Tolkien")
        self.book = Book.objects.create(
            title="The Hobbit", rating=5, author=self.author, slug="the-hobbit")
        self.user = get_user_model().objects.create_user(
            username="tester", password="a-test-only-password")
        self.token = Token.objects.create(user=self.user)

    def login_with_token(self):
        # sends the header:  Authorization: Token <key>
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    # --- reading is public ---

    def test_anyone_can_list_books(self):
        response = self.client.get(reverse("api-book-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "The Hobbit")

    def test_book_detail_includes_author_name(self):
        response = self.client.get(reverse("api-book-detail", args=[self.book.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["author_name"], "J.R.R. Tolkien")

    def test_book_json_has_the_agreed_fields(self):
        response = self.client.get(reverse("api-book-detail", args=[self.book.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_fields = {
            "id", "title", "rating", "author", "author_name",
            "is_bestselling", "slug", "published_countries", "country_names",
        }
        self.assertEqual(set(response.data.keys()), expected_fields)

    def test_book_lists_its_published_countries(self):
        uk = Country.objects.create(name="United Kingdom", code="UK")
        self.book.published_countries.add(uk)
        response = self.client.get(reverse("api-book-detail", args=[self.book.id]))
        self.assertEqual(response.data["published_countries"], [uk.id])
        self.assertEqual(response.data["country_names"], ["United Kingdom (UK)"])

    def test_unknown_book_returns_404(self):
        response = self.client.get(reverse("api-book-detail", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- search and filter (driven by the screen design) ---

    def test_search_finds_book_by_title(self):
        Book.objects.create(title="Dune", rating=4, author=self.author, slug="dune")
        response = self.client.get(reverse("api-book-list"), {"search": "hobbit"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([b["title"] for b in response.data["results"]], ["The Hobbit"])

    def test_search_finds_book_by_author_name(self):
        other = Author.objects.create(first_name="Frank", last_name="Herbert")
        Book.objects.create(title="Dune", rating=4, author=other, slug="dune")
        response = self.client.get(reverse("api-book-list"), {"search": "herbert"})
        self.assertEqual([b["title"] for b in response.data["results"]], ["Dune"])

    def test_bestselling_filter_keeps_only_bestsellers(self):
        Book.objects.filter(id=self.book.id).update(is_bestselling=True)
        Book.objects.create(title="Dune", rating=4, author=self.author, slug="dune")
        response = self.client.get(reverse("api-book-list"), {"bestselling": "true"})
        self.assertEqual([b["title"] for b in response.data["results"]], ["The Hobbit"])

    # --- ordering: ?ordering=title, ?ordering=-title ---

    def titles_for(self, ordering=None):
        params = {"ordering": ordering} if ordering else {}
        response = self.client.get(reverse("api-book-list"), params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [b["title"] for b in response.data["results"]]

    def make_ordered_books(self):
        Book.objects.create(title="Dune", rating=4, author=self.author, slug="dune")
        Book.objects.create(title="Emma", rating=2, author=self.author, slug="emma")
        # with The Hobbit (rating 5): default order is best rating first

    def test_default_order_is_best_rated_first(self):
        self.make_ordered_books()
        self.assertEqual(self.titles_for(), ["The Hobbit", "Dune", "Emma"])

    def test_ordering_by_title_is_a_to_z(self):
        self.make_ordered_books()
        self.assertEqual(self.titles_for("title"), ["Dune", "Emma", "The Hobbit"])

    def test_minus_reverses_the_order(self):
        self.make_ordered_books()
        self.assertEqual(self.titles_for("-title"), ["The Hobbit", "Emma", "Dune"])

    def test_ordering_by_rating_lowest_first(self):
        self.make_ordered_books()
        self.assertEqual(self.titles_for("rating"), ["Emma", "Dune", "The Hobbit"])

    def test_ordering_by_a_field_not_allowed_is_ignored(self):
        self.make_ordered_books()
        # slug is not in ordering_fields, so the default order is used (no error)
        self.assertEqual(self.titles_for("slug"), ["The Hobbit", "Dune", "Emma"])

    # --- pagination: 10 books per page ---

    def make_books(self, how_many):
        Book.objects.bulk_create([
            Book(title=f"Extra {i}", rating=3, author=self.author, slug=f"extra-{i}")
            for i in range(how_many)])

    def test_first_page_has_ten_books_and_a_next_link(self):
        self.make_books(11)  # 12 books in total with The Hobbit
        response = self.client.get(reverse("api-book-list"))
        self.assertEqual(response.data["count"], 12)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_second_page_has_the_rest(self):
        self.make_books(11)
        response = self.client.get(reverse("api-book-list"), {"page": 2})
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIsNone(response.data["next"])
        self.assertIsNotNone(response.data["previous"])

    def test_page_past_the_end_returns_404(self):
        response = self.client.get(reverse("api-book-list"), {"page": 5})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- writing needs a token ---

    def test_create_book_without_token_is_rejected(self):
        response = self.client.post(
            reverse("api-book-list"), {"title": "New Book", "rating": 4})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Book.objects.count(), 1)

    def test_create_book_with_token_works_and_builds_slug(self):
        self.login_with_token()
        response = self.client.post(
            reverse("api-book-list"),
            {"title": "New Book", "rating": 4, "author": self.author.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Book.objects.count(), 2)
        self.assertEqual(response.data["slug"], "new-book")

    def test_create_book_with_countries(self):
        self.login_with_token()
        uk = Country.objects.create(name="United Kingdom", code="UK")
        response = self.client.post(
            reverse("api-book-list"),
            {"title": "New Book", "rating": 4, "published_countries": [uk.id]},
            format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["published_countries"], [uk.id])

    def test_rating_outside_1_to_5_is_rejected(self):
        self.login_with_token()
        response = self.client.post(
            reverse("api-book-list"), {"title": "Bad Rating", "rating": 9})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rating", response.data)

    def test_delete_needs_token(self):
        url = reverse("api-book-detail", args=[self.book.id])
        self.assertEqual(self.client.delete(url).status_code,
                         status.HTTP_401_UNAUTHORIZED)
        self.login_with_token()
        self.assertEqual(self.client.delete(url).status_code,
                         status.HTTP_204_NO_CONTENT)
        self.assertEqual(Book.objects.count(), 0)

    # --- getting a token ---

    def test_login_endpoint_returns_a_token(self):
        response = self.client.post(
            reverse("api-token"),
            {"username": "tester", "password": "a-test-only-password"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["token"], self.token.key)

    def test_wrong_password_gets_no_token(self):
        response = self.client.post(
            reverse("api-token"), {"username": "tester", "password": "wrong"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
