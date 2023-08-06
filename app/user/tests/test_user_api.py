from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse("user:create")
TOKEN_URL = reverse("user:token")
ME_URL = reverse("user:me")


def create_user(**params):
    """
    Create and return a new user
    """
    return get_user_model().objects.create_user(**params)


class PublicUserAPITests(TestCase):
    """
    Test the public features of the user API
    """

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
            "name": "Test Name",
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", res.data)

    def test_create_email_exists_error(self):
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
            "name": "Test Name",
        }
        create_user(**payload)

        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_password_too_short_error(self):
        payload = {"email": "test@example.com", "password": "test", "name": "Test Name"}
        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        user_exists = get_user_model().objects.filter(email=payload["email"]).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """
        Test generating token for valid user credentials
        """
        user_details = {
            "name": "Test Name",
            "email": "test123@email.com",
            "password": "test-user-pass",
        }
        create_user(**user_details)

        payload = {"email": user_details["email"], "password": user_details["password"]}

        res = self.client.post(TOKEN_URL, payload)

        self.assertIn("token", res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_for_bad_credentials(self):
        """
        Test generating returning error for invalid user credentials
        """
        user_details = {
            "name": "Test Name",
            "email": "test123@email.com",
            "password": "test-user-pass",
        }
        create_user(**user_details)

        payload = {"email": user_details["email"], "password": "bad_pass"}

        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn("token", res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """
        Test generating returning error with blank password
        """
        user_details = {
            "name": "Test Name",
            "email": "test123@email.com",
            "password": "test-user-pass",
        }
        create_user(**user_details)

        payload = {"email": user_details["email"], "password": ""}

        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn("token", res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """
        Test authentication is required for user
        """
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    """
    Test requests that require authentication
    """

    def setUp(self):
        self.user_details = dict(
            name="Test Name",
            email="test123@email.com",
            password="test-user-pass",
        )
        self.user = create_user(**self.user_details)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """
        Test retrieving profile for logged in user
        """
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, dict(name="Test Name", email="test123@email.com"))

    def test_post_not_allowed_for_me(self):
        res = self.client.post(ME_URL, {})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        payload = {"name": "Updated Name", "password": "New pass"}
        res = self.client.patch(ME_URL, payload)
        self.user.refresh_from_db()

        self.assertEqual(self.user.name, payload["name"])
        self.assertTrue(self.user.check_password(payload["password"]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
