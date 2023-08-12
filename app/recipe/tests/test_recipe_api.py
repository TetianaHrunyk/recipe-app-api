from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


def create_recipe(user, **params):
    default = {
        "title": "Sample recipe title",
        "time_minutes": 22,
        "price": Decimal("5.25"),
        "description": "Sample description",
        "link": "http://sample.com/recipe.pdf",
    }
    default.update(params)

    recipe = Recipe.objects.create(user=user, **default)
    return recipe


RECIPES_URL = reverse("recipe:recipe-list")


def detail_url(recipe_id):
    return reverse("recipe:recipe-detail", args=[recipe_id])


class PublicRecipeAPITests(TestCase):
    """
    Test unauthenticated API requests
    """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """
        Test auth is required to call API
        """
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """
    Test authenticated API requests
    """

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@example.com", "testpass123"
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by("-id")
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipes_list_limited_to_user(self):
        other_user = get_user_model().objects.create_user(
            "otheruser@example.com", "testpass123"
        )

        create_recipe(user=self.user)
        create_recipe(user=other_user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe_id=recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        payload = {
            "title": "Sample recipe title",
            "time_minutes": 22,
            "price": Decimal("5.25"),
            "description": "Sample description",
            "link": "http://sample.com/recipe.pdf",
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data["id"])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_create_recipe_with_new_tags(self):
        payload = {
            "title": "Sample recipe title",
            "time_minutes": 22,
            "price": Decimal("5.25"),
            "tags": [
                {"name": "Dinner"},
                {"name": "Italian"},
            ],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload["tags"]:
            exists = recipe.tags.filter(name=tag["name"], user=self.user).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        tag_indian = Tag.objects.create(user=self.user, name="Indian")
        payload = {
            "title": "Pongal",
            "time_minutes": 60,
            "price": Decimal("4.25"),
            "tags": [
                {"name": "Indian"},
                {"name": "Breakfast"},
            ],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload["tags"]:
            exists = recipe.tags.filter(name=tag["name"], user=self.user).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        recipe = create_recipe(self.user)
        payload = {
            "tags": [
                {"name": "Lunch"},
            ],
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name=payload["tags"][0]["name"])
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assigned_tag(self):
        tag_breakfast = Tag.objects.create(user=self.user, name="Breakfast")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name="Lunch")

        payload = {"tags": [{"name": "Lunch"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        tag_breakfast = Tag.objects.create(user=self.user, name="Breakfast")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        payload = {"tags": []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)
