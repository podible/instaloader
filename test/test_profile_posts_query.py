import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.getcwd())

from instaloader.exceptions import (ConnectionException, ProfileNoPostsException, ProfileNotExistsException,
                                    ProfileNotFoundException, ProfileUnavailableException)
from instaloader.structures import Profile

CONNECTION = "xdt_api__v1__feed__user_timeline_graphql_connection"
DOC_ID = "29156678094015645"
FRIENDLY_NAME = "PolarisProfilePostsQuery"
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
    "__relay_internal__pv__PolarisSEOIsCrawlerrelayprovider": False,
    "__relay_internal__pv__PolarisThreadsStyleCommentsEnabledrelayprovider": False,
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
        self.query.assert_called_once_with(DOC_ID, EXPECTED_VARIABLES, friendly_name=FRIENDLY_NAME)

    def test_from_username_prefers_owned_post_over_coauthor(self):
        self.query.return_value = timeline([
            {"node": {"user": {"username": "partner", "id": "2"},
                      "coauthor_producers": [{"username": "natgeo", "id": "1", "full_name": "coauthor"}]}},
            {"node": {"user": {"username": "natgeo", "id": "1", "full_name": "owner"}}},
        ])

        profile = Profile.from_username(self.context, "natgeo")

        self.assertEqual(profile._node["full_name"], "owner")

    def test_from_username_matches_coauthor_when_no_post_is_owned(self):
        self.query.return_value = timeline([
            {"node": {"user": {"username": "partner", "id": "2"},
                      "coauthor_producers": [{"username": "other", "id": "3"},
                                             {"username": "natgeo", "id": "1"}]}},
        ])

        profile = Profile.from_username(self.context, "natgeo")

        self.assertEqual((profile.username, profile.userid), ("natgeo", 1))

    def test_from_username_ignores_pending_coauthor_invites(self):
        self.query.return_value = timeline([
            {"node": {"user": {"username": "partner", "id": "2"},
                      "coauthor_producers": [],
                      "invited_coauthor_producers": [{"username": "natgeo", "id": "1"}]}},
        ])

        with self.assertRaises(ProfileNoPostsException):
            Profile.from_username(self.context, "natgeo")

    def test_from_username_ignores_the_case_of_the_requested_name(self):
        self.query.return_value = timeline([{"node": {"user": {"username": "natgeo", "id": "1"}}}])

        profile = Profile.from_username(self.context, "NatGeo")

        self.assertEqual((profile.username, profile.userid), ("natgeo", 1))

    def test_from_username_ignores_the_case_of_a_coauthor(self):
        self.query.return_value = timeline([
            {"node": {"user": {"username": "partner", "id": "2"},
                      "coauthor_producers": [{"username": "natgeo", "id": "1"}]}},
        ])

        profile = Profile.from_username(self.context, "NatGeo")

        self.assertEqual((profile.username, profile.userid), ("natgeo", 1))

    def test_from_username_reports_a_missing_account(self):
        self.query.return_value = {"errors": [{"message": "A server error field_exception occured.",
                                               "code": 1357005}]}

        with self.assertRaisesRegex(ProfileNotFoundException, "gone timeline query with field_exception 1357005"):
            Profile.from_username(self.context, "gone")

    def test_from_username_reports_an_empty_timeline_as_no_posts(self):
        self.query.return_value = timeline([])

        with self.assertRaisesRegex(ProfileNoPostsException, "returned 0 timeline posts for natgeo"):
            Profile.from_username(self.context, "natgeo")

    def test_from_username_keeps_other_failures_generic(self):
        failures = [
            {"errors": [{"message": "Something else", "code": 1}]},
            {"data": {CONNECTION: None}},
            ConnectionException("proxy failed"),
        ]
        for failure in failures:
            with self.subTest(failure=failure):
                self.query.side_effect = failure if isinstance(failure, Exception) else None
                self.query.return_value = failure
                with self.assertRaisesRegex(ProfileNotExistsException, "may have blocked you") as raised:
                    Profile.from_username(self.context, "natgeo")
                self.assertNotIsInstance(raised.exception, ProfileUnavailableException)

    def test_logged_in_get_posts_sends_current_query_on_every_page(self):
        profile = Profile(self.context, {"username": "natgeo", "id": "1"})
        profile._has_full_metadata = True
        self.query.side_effect = [timeline([], end_cursor="cursor-1"), timeline([])]

        list(profile.get_posts())

        first, second = self.query.call_args_list
        self.assertEqual(first.args[:2], (DOC_ID, EXPECTED_VARIABLES))
        self.assertEqual(
            second.args[:2],
            (DOC_ID, {**EXPECTED_VARIABLES, "after": "cursor-1", "before": None, "first": 12, "last": None}),
        )
        self.assertEqual([call.kwargs["friendly_name"] for call in (first, second)], [FRIENDLY_NAME] * 2)

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
        self.assertIsNone(self.query.call_args.kwargs["friendly_name"])
        self.assertFalse(variables["__relay_internal__pv__PolarisFeedShareMenurelayprovider"])
        self.assertEqual(variables["id"], 1)


if __name__ == "__main__":
    unittest.main()
