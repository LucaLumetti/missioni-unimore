from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import HttpResponseRedirect, resolve_url
from django.conf import settings


def get_success_url(request):
    url = request.POST.get('next', request.GET.get('next', ''))
    return url or resolve_url(settings.LOGIN_REDIRECT_URL)


def shibboleth_login(request):
    meta = request.META

    user, created = User.objects.get_or_create(username=meta["eppn"])
    if created:
        user.set_unusable_password()

    if user.email == '' and "mail" in meta:
        user.email = meta["mail"]
    if user.first_name == '' and "givenName" in meta:
        user.first_name = str(meta["givenName"]).capitalize()
    if user.last_name == '' and "sn" in meta:
        user.last_name = str(meta["sn"]).capitalize()
    user.save()

    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)

    request.GET.urlencode()
    return HttpResponseRedirect(get_success_url(request))


def shibboleth_test(request: HttpRequest):
    meta = request.META

    s = '<pre>\n'
    for k, v in meta.items():
        s += k + ': ' + str(v) + '\n'
    s += '</pre>\n'

    return HttpResponse(s)
