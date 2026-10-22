from django.utils.text import slugify
from rest_framework import serializers

from .models import Author, Book


class LoginSerializer(serializers.Serializer):
    # only describes the login request in the docs; DRF's own view does the real checking
    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})


class TokenSerializer(serializers.Serializer):
    # only describes the login response in the docs
    token = serializers.CharField()


class AuthorSerializer(serializers.ModelSerializer):
    # full_name is a method on the Author model; source= lets us expose it as a field
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Author
        fields = ["id", "first_name", "last_name", "full_name"]


class BookSerializer(serializers.ModelSerializer):
    # read-only extra field built from the related Author (null if the book has no author)
    author_name = serializers.CharField(
        source="author.full_name", read_only=True, allow_null=True)
    # the countries as readable text, e.g. "United Kingdom (UK)" (uses Country.__str__)
    country_names = serializers.StringRelatedField(
        source="published_countries", many=True, read_only=True)

    class Meta:
        model = Book
        fields = ["id", "title", "rating", "author", "author_name",
                  "is_bestselling", "slug", "published_countries", "country_names"]
        read_only_fields = ["slug"]
        extra_kwargs = {"published_countries": {"required": False, "allow_empty": True}}

    def create(self, validated_data):
        # the model no longer builds the slug in save(), so build it here
        validated_data["slug"] = slugify(validated_data["title"])
        return super().create(validated_data)
