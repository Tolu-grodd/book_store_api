from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import AuthorViewSet, BookViewSet, LoginView

# The router builds the list/detail URLs for each viewset automatically:
#   /api/books/      /api/books/<id>/      /api/authors/      /api/authors/<id>/
router = DefaultRouter()
router.register("books", BookViewSet, basename="api-book")
router.register("authors", AuthorViewSet, basename="api-author")

urlpatterns = [
    # POST a username and password here to receive a token
    path("token/", LoginView.as_view(), name="api-token"),
    path("", include(router.urls)),
]
