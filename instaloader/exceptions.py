class InstaloaderException(Exception):
    """Base exception for this script.

    :note: This exception should not be raised directly."""
    pass


class QueryReturnedBadRequestException(InstaloaderException):
    pass


class QueryReturnedForbiddenException(InstaloaderException):
    pass


class ProfileNotExistsException(InstaloaderException):
    pass


class ProfileUnavailableException(ProfileNotExistsException):
    """Instagram answered the profile lookup without the profile.

    Unlike other lookup failures, retrying with a different session rarely changes the answer.

    :note: Raised as one of its subclasses.
    """
    pass


class ProfileNotFoundException(ProfileUnavailableException):
    """Instagram answered with a field_exception and no data: the account does not exist, or is private."""
    pass


class ProfileNoPostsException(ProfileUnavailableException):
    """None of the posts on the first page of the timeline is owned or co-authored by the account, including an
    empty timeline: the account is private, or has no posts."""
    pass


class ProfileHasNoPicsException(InstaloaderException):
    """
    .. deprecated:: 4.2.2
       Not raised anymore.
    """
    pass


class PrivateProfileNotFollowedException(InstaloaderException):
    pass


class LoginRequiredException(InstaloaderException):
    pass


class LoginException(InstaloaderException):
    pass


class TwoFactorAuthRequiredException(LoginException):
    pass


class InvalidArgumentException(InstaloaderException):
    pass


class BadResponseException(InstaloaderException):
    pass


class BadCredentialsException(LoginException):
    pass


class ConnectionException(InstaloaderException):
    pass


class PostChangedException(InstaloaderException):
    """.. versionadded:: 4.2.2"""
    pass


class QueryReturnedNotFoundException(ConnectionException):
    pass


class TooManyRequestsException(ConnectionException):
    pass

class IPhoneSupportDisabledException(InstaloaderException):
    pass

class AbortDownloadException(Exception):
    """
    Exception that is not catched in the error catchers inside the download loop and so aborts the
    download loop.

    This exception is not a subclass of ``InstaloaderException``.

    .. versionadded:: 4.7
    """
    pass
