import os
import sys
import unittest

sys.path.insert(0, os.getcwd())

from instaloader.instaloadercontext import InstaloaderContext
from instaloader.structures import Post


def _media(**overrides):
    base = {
        "code": "ABC123",
        "pk": "123456789",
        "media_type": 1,
        "taken_at": 1723276719,
        "caption": None,
        "has_liked": False,
        "like_count": 0,
    }
    base.update(overrides)
    return base


class TestFromIphoneStructEmptyLists(unittest.TestCase):
    def setUp(self):
        self.context = InstaloaderContext(quiet=True, sleep=False)

    def test_empty_candidates_leaves_display_url_unset(self):
        post = Post.from_iphone_struct(self.context, _media(image_versions2={"candidates": []}))

        self.assertNotIn("display_url", post._node)

    def test_candidates_set_display_url(self):
        post = Post.from_iphone_struct(
            self.context,
            _media(image_versions2={"candidates": [{"url": "https://example.com/img.jpg"}]}),
        )

        self.assertEqual(post._node["display_url"], "https://example.com/img.jpg")

    def test_empty_video_versions_skips_video_url_and_keeps_counts(self):
        post = Post.from_iphone_struct(
            self.context,
            _media(media_type=2, video_versions=[], video_duration=3.5, view_count=10),
        )

        self.assertNotIn("video_url", post._node)
        self.assertEqual(post._node["video_duration"], 3.5)
        self.assertEqual(post._node["video_view_count"], 10)

    def test_video_versions_use_the_last_url(self):
        post = Post.from_iphone_struct(
            self.context,
            _media(
                media_type=2,
                video_versions=[
                    {"url": "https://example.com/low.mp4"},
                    {"url": "https://example.com/high.mp4"},
                ],
            ),
        )

        self.assertEqual(post._node["video_url"], "https://example.com/high.mp4")

    def test_carousel_empty_lists_do_not_raise(self):
        post = Post.from_iphone_struct(
            self.context,
            _media(
                media_type=8,
                carousel_media=[
                    {"pk": "1", "media_type": 1, "image_versions2": {"candidates": []}},
                    {
                        "pk": "2",
                        "media_type": 2,
                        "image_versions2": {"candidates": [{"url": "https://example.com/slide.jpg"}]},
                        "video_versions": [],
                    },
                ],
            ),
        )

        first, second = (edge["node"] for edge in post._node["edge_sidecar_to_children"]["edges"])
        self.assertEqual(first["display_url"], "")
        self.assertNotIn("video_url", first)
        self.assertEqual(second["display_url"], "https://example.com/slide.jpg")
        self.assertNotIn("video_url", second)

    def test_carousel_video_uses_the_first_version(self):
        post = Post.from_iphone_struct(
            self.context,
            _media(
                media_type=8,
                carousel_media=[
                    {
                        "pk": "2",
                        "media_type": 2,
                        "image_versions2": {"candidates": [{"url": "https://example.com/slide.jpg"}]},
                        "video_versions": [
                            {"url": "https://example.com/a.mp4"},
                            {"url": "https://example.com/b.mp4"},
                        ],
                    }
                ],
            ),
        )

        node = post._node["edge_sidecar_to_children"]["edges"][0]["node"]
        self.assertEqual(node["video_url"], "https://example.com/a.mp4")


if __name__ == "__main__":
    unittest.main()
