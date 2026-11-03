import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.getcwd())

from instaloader.structures import Profile

DOC_ID = "40158838120366999"
FRIENDLY_NAME = "PolarisProfilePageContentQuery"
EXPECTED_VARIABLES = {
    "enable_integrity_filters": True,
    "id": "80198986389",
    "__relay_internal__pv__PolarisCannesGuardianExperienceEnabledrelayprovider": True,
    "__relay_internal__pv__PolarisCASB976ProfileEnabledrelayprovider": False,
    "__relay_internal__pv__PolarisProfileInformTreatmentBannerEnabledrelayprovider": False,
    "__relay_internal__pv__PolarisWebSchoolsEnabledrelayprovider": False,
    "__relay_internal__pv__PolarisProfileRingsGradientEnabledrelayprovider": True,
    "__relay_internal__pv__PolarisRepostsConsumptionEnabledrelayprovider": True,
    "__relay_internal__pv__PolarisShortDramaEnabledrelayprovider": True,
}
# Trimmed PolarisProfilePageContentQuery response captured from the web app.
RESPONSE = {
    "data": {
        "user": {
            "pk": "80198986389",
            "id": "80198986389",
            "username": "dimablackmetal",
            "full_name": "Dzmirty Chasniuk",
            "biography": "Black Metal Guitarist & Composer",
            "is_private": False,
            "profile_pic_url": "https://cdn/pic-150.jpg",
            "hd_profile_pic_url_info": {"url": "https://cdn/pic-hd.jpg"},
            "follower_count": 62,
            "following_count": 96,
            "media_count": 34,
            "friendship_status": {"following": True, "followed_by": True, "blocking": False},
        },
        "viewer": {"user": {"pk": "35318319504", "id": "35318319504"}},
    },
    "extensions": {"is_final": True},
}


class TestProfilePageQuery(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock(is_logged_in=True, iphone_support=False)
        self.query = self.context.doc_id_graphql_query
        self.query.return_value = RESPONSE

    def test_metadata_sends_current_query(self):
        # Timeline nodes carry no biography, so reading it loads the profile page query.
        profile = Profile(self.context, {"username": "dimablackmetal", "id": "80198986389"})

        self.assertEqual(profile.biography, "Black Metal Guitarist & Composer")

        self.query.assert_called_once_with(DOC_ID, EXPECTED_VARIABLES, friendly_name=FRIENDLY_NAME)

    def test_metadata_reads_feed_fields_from_response(self):
        profile = Profile(self.context, {"username": "dimablackmetal", "id": "80198986389"})

        self.assertEqual(
            (profile.full_name, profile.biography, profile.profile_pic_url, profile.followers, profile.mediacount),
            ("Dzmirty Chasniuk", "Black Metal Guitarist & Composer", "https://cdn/pic-hd.jpg", 62, 34),
        )
        self.query.assert_called_once()

    def test_from_id_sends_current_query(self):
        self.context.profile_id_cache = {}

        profile = Profile.from_id(self.context, 80198986389)

        self.assertEqual((profile.username, profile.userid), ("dimablackmetal", 80198986389))
        self.query.assert_called_once_with(DOC_ID, EXPECTED_VARIABLES, friendly_name=FRIENDLY_NAME)


if __name__ == "__main__":
    unittest.main()
