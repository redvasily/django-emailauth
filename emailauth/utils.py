from django.conf import settings
from django.http import Http404
from django.utils.functional import curry

def email_verification_days():
    return getattr(settings, 'EMAILAUTH_VERIFICATION_DAYS', 3)

def use_single_email():
    return getattr(settings, 'EMAILAUTH_USE_SINGLE_EMAIL', True)

def use_automaintenance():
    return getattr(settings, 'EMAILAUTH_USE_AUTOMAINTENANCE', True)

def require_emailauth_mode(func, emailauth_use_singe_email):
    def wrapper(*args, **kwds):
        if use_single_email() == emailauth_use_singe_email:
            return func(*args, **kwds)
        else:
            raise Http404()
    return wrapper

requires_single_email_mode = curry(require_emailauth_mode,
    emailauth_use_singe_email=True)

requires_multi_emails_mode = curry(require_emailauth_mode,
    emailauth_use_singe_email=False)
