import unittest
from unittest.mock import patch, Mock

import pandas as pd
import requests

from api_client import fetch_posts
from data_parser import parse_posts


class TestAPIClient(unittest.TestCase):

    @patch("api_client.requests.get")
    def test_fetch_posts_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = [{"id": 1}]
        mock_get.return_value = mock_response

        result = fetch_posts()

        self.assertEqual(result, [{"id": 1}])
        mock_get.assert_called_once_with(
            "https://jsonplaceholder.typicode.com/posts",
            timeout=10
        )

    @patch("api_client.requests.get")
    def test_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = (
            requests.HTTPError("Server error")
        )
        mock_get.return_value = mock_response

        with self.assertRaises(requests.HTTPError):
            fetch_posts()


class TestDataParser(unittest.TestCase):

    def test_valid_post(self):
        posts = [{
            "id": 1,
            "userId": 2,
            "title": " Hello ",
            "body": " World "
        }]

        result = parse_posts(posts)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["title"], "Hello")
        self.assertIsInstance(result, pd.DataFrame)

    def test_invalid_post_is_skipped(self):
        posts = [{
            "id": 1,
            "userId": 2,
            "title": "",
            "body": "Missing title"
        }]

        result = parse_posts(posts)

        self.assertTrue(result.empty)

    def test_wrong_input_raises_error(self):
        with self.assertRaises(ValueError):
            parse_posts({"id": 1})


if __name__ == "__main__":
    unittest.main()