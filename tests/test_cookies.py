import uuid

import pytest

from pyramid.interfaces import IAuthenticationPolicy
from webob import Request
from zope.interface.verify import verifyObject

from pyramid_jwt.policy import JWTTokenAuthenticationPolicy


@pytest.fixture(scope='module')
def principal():
    return str(uuid.uuid4())


@pytest.fixture(scope='module')
def request():
    return Request.blank('/')


def test_interface():
    verifyObject(IAuthenticationPolicy, JWTTokenAuthenticationPolicy('secret'))


def test_cookie(request, principal):
    policy = JWTTokenAuthenticationPolicy('secret')
    cookie = policy.remember(request, principal).pop()

    assert len(cookie) == 2

    header, cookie = cookie
    assert header == 'Set-Cookie'
    assert len(cookie) > 0


def test_cookie_name(request, principal):
    policy = JWTTokenAuthenticationPolicy('secret', cookie_name='auth')
    _, cookie = policy.remember(request, principal).pop()

    name, value = cookie.split('=', 1)
    assert name == 'auth'


def test_secure_cookie():
    policy = JWTTokenAuthenticationPolicy('secret', https_only=True)
    request = Request.blank('/')
    _, cookie = policy.remember(request, str(uuid.uuid4())).pop()

    assert '; secure;' in cookie
    assert '; HttpOnly' in cookie


def test_insecure_cookie(request, principal):
    policy = JWTTokenAuthenticationPolicy('secret', https_only=False)
    _, cookie = policy.remember(request, principal).pop()

    assert '; secure;' not in cookie
    assert '; HttpOnly' in cookie


def test_cookie_decode(request, principal):
    policy = JWTTokenAuthenticationPolicy('secret', https_only=False)

    header, cookie = policy.remember(request, principal).pop()
    name, value = cookie.split('=', 1)

    value, _ = value.split(';', 1)
    request.cookies = {name: value}

    claims = policy.get_claims(request)
    assert claims['sub'] == principal


def test_cookie_max_age(request, principal):
    policy = JWTTokenAuthenticationPolicy('secret', cookie_name='auth',
                                          expiration=100)
    _, cookie = policy.remember(request, principal).pop()
    _, value = cookie.split('=', 1)

    _, meta = value.split(';', 1)
    assert 'Max-Age=100' in meta
    assert "expires" in meta


@pytest.mark.freeze_time
def test_expired_token(request, principal, freezer):
    policy = JWTTokenAuthenticationPolicy('secret', cookie_name='auth',
                                          expiration=1)
    _, cookie = policy.remember(request, principal).pop()
    name, value = cookie.split('=', 1)

    freezer.tick(delta=2)

    value, _ = value.split(';', 1)
    request.cookies = {name: value}
    claims = policy.get_claims(request)

    assert claims == {}
