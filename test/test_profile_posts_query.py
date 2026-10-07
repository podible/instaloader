import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.getcwd())

from instaloader.structures import Profile

CONNECTION = "xdt_api__v1__feed__user_timeline_graphql_connection"
EXPECTED_VARIABLES = {
    "data": {
        "count": 12,
        "include_reel_media_seen_timestamp": True,
        "include_relationship_info": True,
        "latest_besties_reel_media": True,
        "latest_reel_media": True,
    },
    "username": "natgeo",
    "__relay_internal__pv__PolarisMultiCaptionCarouselEnabledrelayprovider": True,
    "__relay_internal__pv__PolarisShortDramaEnabledrelayprovider": True,
    "__relay_internal__pv__PolarisReelsRecoDebugOverlayEnabledrelayprovider": False,
}


def timeline(edges, end_cursor=None):
    page_info = {"has_next_page": end_cursor is not None, "end_cursor": end_cursor}
    return {"data": {CONNECTION: {"edges": edges, "page_info": page_info}}}


class TestProfilePostsQuery(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock(is_logged_in=True)
        self.query = self.context.doc_id_graphql_query

    def test_from_username_sends_current_query(self):
        self.query.return_value = timeline([{"node": {"user": {"username": "natgeo", "id": "1"}}}])

        profile = Profile.from_username(self.context, "natgeo")

        self.assertEqual(profile.username, "natgeo")
        self.query.assert_called_once_with("28542612348729311", EXPECTED_VARIABLES)

    def test_logged_in_get_posts_sends_current_query_on_every_page(self):
        profile = Profile(self.context, {"username": "natgeo", "id": "1"})
        profile._has_full_metadata = True
        self.query.side_effect = [timeline([], end_cursor="cursor-1"), timeline([])]

        list(profile.get_posts())

        first, second = self.query.call_args_list
        self.assertEqual(first.args[:2], ("28542612348729311", EXPECTED_VARIABLES))
        self.assertEqual(
            second.args[:2],
            (
                "28542612348729311",
                {**EXPECTED_VARIABLES, "after": "cursor-1", "before": None, "first": 12, "last": None},
            ),
        )

    def test_anonymous_get_posts_keeps_legacy_query(self):
        self.context.is_logged_in = False
        profile = Profile(self.context, {"username": "natgeo", "id": "1"})
        profile._has_full_metadata = True
        profile._node["edge_owner_to_timeline_media"] = {
            "edges": [],
            "page_info": {"has_next_page": True, "end_cursor": "cursor-1"},
        }
        self.query.return_value = {"data": {"user": {"edge_owner_to_timeline_media": {"edges": []}}}}

        list(profile.get_posts())

        doc_id, variables, _ = self.query.call_args.args
        self.assertEqual(doc_id, "7950326061742207")
        self.assertFalse(variables["__relay_internal__pv__PolarisFeedShareMenurelayprovider"])
        self.assertEqual(variables["id"], 1)


if __name__ == "__main__":
    unittest.main()
