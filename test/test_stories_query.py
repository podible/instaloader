import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock

sys.path.insert(0, os.getcwd())

from instaloader import Instaloader
from instaloader.structures import Profile

DOC_ID = "29170422829314651"
FRIENDLY_NAME = "PolarisStoriesV3ReelPageStandaloneQuery"


def video_item(pk, taken_at):
    return {
        "pk": pk,
        "id": f"{pk}_787132",
        "media_type": 2,
        "taken_at": taken_at,
        "expiring_at": taken_at + 86400,
        "caption": None,
        "image_versions2": {"candidates": [{"url": f"https://cdn/{pk}-large.jpg", "width": 1080, "height": 1920},
                                           {"url": f"https://cdn/{pk}-small.jpg", "width": 640, "height": 1138}]},
        "video_versions": [{"type": 101, "url": f"https://cdn/{pk}-720.mp4"},
                           {"type": 102, "url": f"https://cdn/{pk}-480.mp4"}],
    }


def image_item(pk, taken_at):
    return {
        "pk": pk,
        "id": f"{pk}_787132",
        "media_type": 1,
        "taken_at": taken_at,
        "expiring_at": taken_at + 86400,
        "caption": {"text": "Look up"},
        "image_versions2": {"candidates": [{"url": f"https://cdn/{pk}.jpg", "width": 1080, "height": 1920}]},
        "video_versions": None,
    }


def reels_media(*items):
    reel = {
        "id": "787132",
        "latest_reel_media": items[-1]["taken_at"],
        "seen": 0,
        "user": {"pk": "787132", "id": "787132", "username": "natgeo"},
        "items": list(items),
    }
    return {"data": {"xdt_api__v1__feed__reels_media": {"reels_media": [reel]}, "xdt_viewer": {}}}


class TestStoriesQuery(unittest.TestCase):
    def setUp(self):
        self.loader = Instaloader(iphone_support=False, quiet=True)
        self.loader.context = MagicMock(is_logged_in=True, iphone_support=False)
        self.query = self.loader.context.doc_id_graphql_query

    def test_get_stories_sends_current_query(self):
        self.query.return_value = reels_media(video_item("1", 1793282408))

        list(self.loader.get_stories([787132]))

        self.query.assert_called_once_with(
            DOC_ID,
            {"reel_ids_arr": ["787132"],
             "__relay_internal__pv__PolarisCommunityNoteStoriesLabelEnabledrelayprovider": True},
            friendly_name=FRIENDLY_NAME,
        )
        self.loader.context.graphql_query.assert_not_called()

    def test_story_items_from_reels_media(self):
        self.query.return_value = reels_media(video_item("1", 1793282408), image_item("2", 1793301358))

        [story] = list(self.loader.get_stories([787132]))
        video, image = sorted(story.get_items(), key=lambda item: item.mediaid)

        self.assertEqual((story.owner_username, story.owner_id, story.itemcount), ("natgeo", 787132, 2))
        self.assertEqual(story.latest_media_utc, datetime.utcfromtimestamp(1793301358))
        self.assertEqual((video.mediaid, video.typename, video.is_video), (1, "GraphStoryVideo", True))
        self.assertEqual(video.video_url, "https://cdn/1-720.mp4")
        self.assertEqual(video.url, "https://cdn/1-large.jpg")
        self.assertEqual(video.date_utc, datetime.utcfromtimestamp(1793282408))
        self.assertIsNone(video.caption)
        self.assertEqual((image.typename, image.is_video, image.video_url), ("GraphStoryImage", False, None))
        self.assertEqual((image.url, image.caption), ("https://cdn/2.jpg", "Look up"))
        self.assertEqual(image.owner_username, "natgeo")
        self.loader.context.get_iphone_json.assert_not_called()


class TestHasPublicStory(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock(is_logged_in=True)

    def test_reads_latest_reel_media_from_profile_posts_node(self):
        with_story = Profile(self.context, {"username": "natgeo", "id": "1", "latest_reel_media": 1793301358})
        without_story = Profile(self.context, {"username": "quiet", "id": "2", "latest_reel_media": 0})

        self.assertTrue(with_story.has_public_story)
        self.assertFalse(without_story.has_public_story)
        self.context.graphql_query.assert_not_called()

    def test_falls_back_to_legacy_query_without_latest_reel_media(self):
        profile = Profile(self.context, {"username": "natgeo", "id": "1"})
        profile._has_full_metadata = True
        self.context.graphql_query.return_value = {"data": {"user": {"has_public_story": True}}}

        self.assertTrue(profile.has_public_story)
        self.assertEqual(self.context.graphql_query.call_args.args[0], "9ca88e465c3f866a76f7adee3871bdd8")


if __name__ == "__main__":
    unittest.main()
