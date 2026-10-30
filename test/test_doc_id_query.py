import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, os.getcwd())

from instaloader.exceptions import AbortDownloadException, ConnectionException
from instaloader.instaloadercontext import InstaloaderContext
from instaloader.structures import Post

PAGE = '<script>{"define":[["DTSGInitialData",[],{"token":"NAf-token:1:2"},258]]}</script>'
LOGGED_OUT_PAGE = '<script>{"define":[["LSD",[],{"token":"lsd-token"},323]]}</script>'
MEDIA = {"pk": "1", "id": "1_2", "code": "abc", "media_type": 1, "taken_at": 1700000000,
         "user": {"pk": "2", "username": "owner"}, "like_count": 5, "comment_count": 2}


class TestDocIdQuery(unittest.TestCase):
    def setUp(self):
        self.context = InstaloaderContext(sleep=False, quiet=True)
        self.context.username = "acct"
        # The anonymous session already holds login()'s empty sessionid seed (no domain); this is the real one.
        self.context._session.cookies.set("csrftoken", "csrf", domain=".instagram.com")
        self.context._session.cookies.set("sessionid", "s1", domain=".instagram.com")
        self.page_response = MagicMock(text=PAGE, url="https://www.instagram.com/", status_code=200, is_redirect=False)
        self.page_sessionids = []

        def fake_get(session, url, **kwargs):
            self.page_sessionids.append([c.value for c in session.cookies if c.name == "sessionid"])
            return self.page_response

        patcher = patch.object(requests.Session, "get", autospec=True, side_effect=fake_get)
        self.page = patcher.start()
        self.addCleanup(patcher.stop)
        self.sent = []

        def get_json(path, params, session, use_post):
            self.sent.append((path, params, dict(session.headers)))
            return {"status": "ok"}

        self.context.get_json = get_json

    def test_logged_in_query_sends_page_token_and_browser_headers(self):
        self.context.doc_id_graphql_query("123", {"a": 1}, friendly_name="PolarisProfilePostsQuery")

        path, params, headers = self.sent[0]
        self.assertEqual(path, "graphql/query")
        self.assertEqual(params["fb_dtsg"], "NAf-token:1:2")
        self.assertEqual(params["doc_id"], "123")
        self.assertEqual(headers["sec-fetch-site"], "same-origin")
        self.assertEqual(headers["x-fb-friendly-name"], "PolarisProfilePostsQuery")
        self.page.assert_called_once()
        self.assertEqual(self.page.call_args.args[1], "https://www.instagram.com/")

    def test_page_is_fetched_with_the_real_sessionid_only(self):
        self.assertEqual(
            sorted(bool(c.value) for c in self.context._session.cookies if c.name == "sessionid"), [False, True]
        )

        self.context.doc_id_graphql_query("123", {})

        self.assertEqual(self.page_sessionids, [["s1"]])

    def test_token_is_reused_until_the_session_changes(self):
        self.context.doc_id_graphql_query("123", {})
        self.context.doc_id_graphql_query("123", {})
        self.assertEqual(self.page.call_count, 1)

        self.context._session.cookies.set("sessionid", "s2", domain=".instagram.com")
        self.context.doc_id_graphql_query("123", {})
        self.assertEqual(self.page.call_count, 2)

    def test_missing_token_raises(self):
        self.page_response = MagicMock(
            text="<html>login</html>", url="https://www.instagram.com/accounts/login/", status_code=200,
            is_redirect=False,
        )

        with self.assertRaisesRegex(ConnectionException, "accounts/login/ \\(HTTP 200, 18 bytes\\)"):
            self.context.doc_id_graphql_query("123", {})
        self.assertEqual(self.sent, [])

    def test_redirected_home_page_aborts(self):
        self.page_response = MagicMock(
            status_code=302, is_redirect=True, headers={"location": "https://www.instagram.com/?next=%2F&fb_dtsg=x"}
        )

        with self.assertRaisesRegex(AbortDownloadException, r"redirected to https://www.instagram.com/$"):
            self.context.doc_id_graphql_query("123", {})
        self.assertFalse(self.page.call_args.kwargs["allow_redirects"])
        self.assertEqual(self.sent, [])

    def test_anonymous_query_skips_token(self):
        self.context.username = None

        self.context.doc_id_graphql_query("123", {})

        path, params, headers = self.sent[0]
        self.assertEqual(path, "graphql/query")
        self.assertNotIn("fb_dtsg", params)
        self.assertNotIn("lsd", params)
        self.assertNotIn("x-fb-friendly-name", headers)
        self.page.assert_not_called()

    def test_web_api_query_sends_the_start_page_lsd_to_api_graphql(self):
        self.context.username = None
        self.page_response = MagicMock(text=LOGGED_OUT_PAGE, url="https://www.instagram.com/", status_code=200)

        self.context.doc_id_graphql_query("123", {}, web_api=True)
        self.context.doc_id_graphql_query("456", {}, web_api=True)

        path, params, headers = self.sent[1]
        self.assertEqual(path, "api/graphql")
        self.assertEqual(params["lsd"], "lsd-token")
        self.assertEqual(params["doc_id"], "456")
        self.assertNotIn("fb_dtsg", params)
        self.assertEqual(headers["x-fb-lsd"], "lsd-token")
        self.assertEqual(headers["sec-fetch-mode"], "cors")
        self.page.assert_called_once()
        self.assertEqual(self.page.call_args.kwargs["headers"]["Sec-Fetch-Mode"], "navigate")

    def test_missing_lsd_raises(self):
        self.context.username = None
        self.page_response = MagicMock(text="<html>error</html>", url="https://www.instagram.com/", status_code=200)

        with self.assertRaisesRegex(ConnectionException, "lsd not found"):
            self.context.doc_id_graphql_query("123", {}, web_api=True)
        self.assertEqual(self.sent, [])


class TestPostMetadataEndpoint(unittest.TestCase):
    def _queried_with(self, username):
        context = InstaloaderContext(sleep=False, quiet=True)
        context.username = username
        context.doc_id_graphql_query = MagicMock(return_value={
            "data": {"xdt_api__v1__media__shortcode__web_info": {"items": [MEDIA]}}})

        Post(context, {"shortcode": "abc"})._obtain_metadata()

        return context.doc_id_graphql_query.call_args.kwargs

    def test_logged_out_post_query_uses_the_web_api(self):
        self.assertEqual(self._queried_with(None), {"web_api": True})

    def test_logged_in_post_query_keeps_graphql_query(self):
        self.assertEqual(self._queried_with("acct"), {"web_api": False})


if __name__ == "__main__":
    unittest.main()
