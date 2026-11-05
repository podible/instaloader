import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, os.getcwd())

from instaloader.exceptions import AbortDownloadException, BadResponseException, ConnectionException
from instaloader.instaloadercontext import InstaloaderContext
from instaloader.structures import Post

SHORTCODE = "DcbU-sERPUe"
VIDEO_URL = "https://scontent.cdninstagram.com/o1/v/t2/f2/m86/reel.mp4?_nc_cat=110&oe=6A0B2C3D"


def media(code, video_url):
    # Trimmed xig_fetch_media of a reels page captured from the web app.
    return {
        "code": code,
        "id": "3970859765311272222_8474803249",
        "pk": "3970859765311272222",
        "media_type": 2,
        "taken_at": 1787583467,
        "user": {"id": "8474803249", "pk": "8474803249", "username": "realmomsofbravo"},
        "image_versions2": {"candidates": [{"url": "https://scontent.cdninstagram.com/cover.jpg"}]},
        "video_versions": [{"type": 101, "url": video_url}],
        "caption": {"text": "Reel caption"},
        "like_count": 12,
        "comment_count": 3,
        "carousel_media": None,
        "usertags": None,
        "location": None,
    }


def script(data):
    payload = {"require": [["RelayPrefetchedStreamCache", "next", [], ["adp_Query", {"__bbox": {"result": {"data": data}}}]]]}
    return f'<script type="application/json" data-sjs>{json.dumps(payload)}</script>'


def page(*data, status=200, location=None):
    resp = MagicMock(status_code=status, is_redirect=location is not None, headers={"location": location})
    resp.text = "<html>" + "".join(script(d) for d in data) + "</html>"
    return resp


class TestReelsPage(unittest.TestCase):
    def setUp(self):
        self.context = InstaloaderContext(sleep=False, quiet=True)
        self.context._session = requests.Session()
        self.context._session.cookies.set("sessionid", "live-session")
        self.page_session = MagicMock()
        self.page_session.__enter__.return_value = self.page_session
        patcher = patch.object(self.context, "get_anonymous_session", return_value=self.page_session)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_reel_comes_from_the_logged_in_reels_page(self):
        # The page also embeds the next reel of the feed.
        self.page_session.get.return_value = page(
            {"xdt_notification_badge": {}},
            {"xig_fetch_media": media(SHORTCODE, VIDEO_URL)},
            {"xig_fetch_media": media("DcZeDu7KYzY", "https://scontent.cdninstagram.com/next.mp4")},
        )

        post = Post.from_reels_page(self.context, SHORTCODE)

        self.assertEqual(post.video_url, VIDEO_URL)
        self.assertEqual(post.mediaid, 3970859765311272222)
        self.assertEqual(post.owner_username, "realmomsofbravo")
        self.assertEqual(post.caption, "Reel caption")
        self.assertEqual(self.page_session.get.call_args.args[0], f"https://www.instagram.com/reels/{SHORTCODE}/")
        self.assertEqual(self.page_session.cookies.get("sessionid"), "live-session")

    def test_page_without_the_reel_raises(self):
        # Pages of some sessions show the reels feed without the reel.
        self.page_session.get.return_value = page({"xdt_api__v1__clips__home__connection_v2": {"edges": []}})

        with self.assertRaisesRegex(BadResponseException, "does not embed the reel"):
            Post.from_reels_page(self.context, SHORTCODE)

    def test_redirect_of_logged_in_page_names_the_target(self):
        self.page_session.get.return_value = page(
            status=302, location="https://www.instagram.com/accounts/suspended/?next=%2Freels%2F")

        with self.assertRaisesRegex(AbortDownloadException, r"redirected to https://www.instagram.com/accounts/suspended/$"):
            Post.from_reels_page(self.context, SHORTCODE)

    def test_logged_out_page_redirect_stays_a_connection_error(self):
        self.page_session.get.return_value = page(status=302, location="https://www.instagram.com/accounts/login/")

        with self.assertRaisesRegex(ConnectionException, "HTTP 302"):
            self.context.get_page("reels/x/")
        self.assertNotIn("live-session", str(self.page_session.cookies))


if __name__ == "__main__":
    unittest.main()
