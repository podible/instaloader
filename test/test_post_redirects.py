import json
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.getcwd())

from instaloader.exceptions import AbortDownloadException
from instaloader.instaloadercontext import InstaloaderContext

CONSENT = "https://www.instagram.com/consent/?flow=user_cookie_choice_v2&source=pft_user_cookie_choice"
SUSPENDED = "https://www.instagram.com/accounts/suspended/?next=https%3A%2F%2Fwww.instagram.com%2F%26fb_dtsg%3DNAf"
PARAMS = {"doc_id": "123", "variables": "{}", "fb_dtsg": "NAf-secret"}


def redirect(location):
    return MagicMock(status_code=302, is_redirect=True, headers={"location": location})


def page(status=200, body=None):
    content_type = "text/html" if body is None else "application/json"
    resp = MagicMock(status_code=status, is_redirect=False, headers={"Content-Type": content_type}, reason="X")
    resp.text = '<html>{"canonicalRouteName":"comet.igweb.PolarisErrorRoute"}</html>' if body is None else "{}"
    resp.json.side_effect = json.JSONDecodeError("not json", "<html>", 0) if body is None else None
    resp.json.return_value = body
    return resp


class TestPostRedirects(unittest.TestCase):
    def setUp(self):
        self.context = InstaloaderContext(sleep=False, quiet=True)
        self.context.username = "acct"
        self.session = MagicMock()

    def query(self):
        return self.context.get_json("graphql/query", params=PARAMS, session=self.session, use_post=True)

    def test_redirect_chain_is_named_without_resending_the_query(self):
        self.session.post.return_value = redirect(CONSENT)
        self.session.get.side_effect = [redirect(SUSPENDED), page()]

        with self.assertRaises(AbortDownloadException) as caught:
            self.query()

        message = str(caught.exception)
        self.assertIn("redirected to https://www.instagram.com/consent/ -> https://www.instagram.com/accounts/suspended/",
                      message)
        self.assertNotIn("NAf", message)
        self.session.post.assert_called_once()
        self.assertEqual([c.args[0] for c in self.session.get.call_args_list], [CONSENT, SUSPENDED])
        self.assertTrue(all("params" not in c.kwargs for c in self.session.get.call_args_list))

    def test_redirect_loop_stops(self):
        self.session.post.return_value = redirect("https://www.instagram.com/")
        self.session.get.return_value = redirect("https://www.instagram.com/")

        with self.assertRaisesRegex(AbortDownloadException, "redirected to https://www.instagram.com/"):
            self.query()

        self.assertEqual(self.session.get.call_count, 4)

    def test_html_reply_aborts_without_retry(self):
        self.session.post.return_value = page()

        with self.assertRaisesRegex(AbortDownloadException, r"returned an HTML page \(comet.igweb.PolarisErrorRoute\)"):
            self.query()

        self.session.post.assert_called_once()

    def test_retry_stays_a_post(self):
        self.session.post.side_effect = [page(status=500), page(body={"status": "ok", "data": {}})]

        self.assertEqual(self.query(), {"status": "ok", "data": {}})

        self.assertEqual(self.session.post.call_count, 2)
        self.session.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
