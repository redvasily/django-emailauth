from datetime import datetime, timedelta

import django.core.mail
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.contrib.sites.models import Site, RequestSite
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required

from emailauth.forms import (LoginForm, RegistrationForm,
    PasswordResetRequestForm, PasswordResetForm, AddEmailForm, DeleteEmailForm,
    ConfirmationForm)
from emailauth.models import UserEmail

from emailauth.utils import (use_single_email, requires_single_email_mode,
    requires_multi_emails_mode, email_verification_days)


# TODO: add better cookie support test
def login(request, template_name='emailauth/login.html',
    redirect_field_name=REDIRECT_FIELD_NAME):

    redirect_to = request.REQUEST.get(redirect_field_name, '')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL
            from django.contrib.auth import login
            login(request, form.get_user())
            #if request.session.test_cookie_worked():
            #    request.session.delete_test_cookie()
            return HttpResponseRedirect(redirect_to)
    else:
        form = LoginForm()

    if Site._meta.installed:
        current_site = Site.objects.get_current()
    else:
        current_site = RequestSite(request)

    return render_to_response(template_name, {
            'form': form,
            redirect_field_name: redirect_to,
            'site_name': current_site.name,
        },
        context_instance=RequestContext(request))


@login_required
def account(request, template_name=None):
    context = RequestContext(request)

    if template_name is None:
        if use_single_email():
            template_name = 'emailauth/account_single_email.html'
        else:
            template_name = 'emailauth/account.html'

    # Maybe move this emails into context processors?
    extra_emails = UserEmail.objects.filter(user=request.user, default=False,
        verified=True)
    unverified_emails = UserEmail.objects.filter(user=request.user,
        default=False, verified=False)

    return render_to_response(template_name, 
        {
            'extra_emails': extra_emails,
            'unverified_emails': unverified_emails,
        },
        context_instance=context)


def get_max_length(model, field_name):
    field = model._meta.get_field_by_name(field_name)[0]
    return field.max_length


def default_register_callback(form, email):
    data = form.cleaned_data
    user = User()
    user.first_name = data['first_name']
    user.is_active = False
    user.email = email.email
    user.set_password(data['password1'])
    user.save()
    user.username = ('id_%d_%s' % (user.id, user.email))[
        :get_max_length(User, 'username')]
    user.save()
    email.user = user


def register(request, callback=default_register_callback):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email_obj = UserEmail.objects.create_unverified_email(
                form.cleaned_data['email'])
            email_obj.send_verification_email(form.cleaned_data['first_name'])

            if callback is not None:
                callback(form, email_obj)

            site = Site.objects.get_current()
            email_obj.user.message_set.create(message='Welcome to %s.' % site.name)

            email_obj.save()
            return HttpResponseRedirect(reverse('emailauth_register_continue',
                args=[email_obj.email]))
    else:
        form = RegistrationForm()

    return render_to_response('emailauth/register.html', {'form': form},
        RequestContext(request))


def register_continue(request, email,
    template_name='emailauth/register_continue.html'):

    return render_to_response(template_name, {'email': email},
        RequestContext(request))


def default_verify_callback(request, email):
    email.user.is_active = True
    email.user.save()

    if request.user.is_anonymous():
        from django.contrib.auth import login
        user = email.user
        user.backend = 'emailauth.backends.EmailBackend'
        login(request, user)
        return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
    else:
        return HttpResponseRedirect(reverse('emailauth_account'))


def verify(request, verification_key, template_name='emailauth/verify.html',
    extra_context=None, callback=default_verify_callback):

    verification_key = verification_key.lower() # Normalize before trying anything with it.
    email = UserEmail.objects.verify(verification_key)

    
    if email is not None:
        email.user.message_set.create(message='%s email confirmed.' % email.email)

        if use_single_email():
            email.default = True
            email.save()
            UserEmail.objects.filter(user=email.user, default=False).delete()

    if email is not None and callback is not None:
        cb_result = callback(request, email)
        if cb_result is not None:
            return cb_result

    context = RequestContext(request)
    if extra_context is not None:
        for key, value in extra_context.items():
            context[key] = value() if callable(value) else value

    return render_to_response(template_name,
        {
            'email': email,
            'expiration_days': email_verification_days(),
        },
        context_instance=context)


def request_password_reset(request,
    template_name='emailauth/request_password.html'):

    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user_email = UserEmail.objects.get(email=email)
            user_email.make_new_key()
            user_email.save()

            current_site = Site.objects.get_current()

            subject = render_to_string(
                'emailauth/request_password_email_subject.txt',
                {'site': current_site})
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())

            message = render_to_string('emailauth/request_password_email.txt', {
                'reset_code': user_email.verification_key,
                'expiration_days': email_verification_days(),
                'site': current_site,
                'first_name': user_email.user.first_name,
            })

            django.core.mail.send_mail(subject, message,
                settings.DEFAULT_FROM_EMAIL, [email])

            return HttpResponseRedirect(
                reverse('emailauth_request_password_reset_continue',
                args=[email]))
    else:
        form = PasswordResetRequestForm()

    context = RequestContext(request)
    return render_to_response(template_name,
        {
            'form': form,
            'expiration_days': email_verification_days(),
        },
        context_instance=context)


def request_password_reset_continue(request, email,
    template_name='emailauth/reset_password_continue.html'):

    return render_to_response(template_name,
        {'email': email},
        context_instance=RequestContext(request))


def reset_password(request, reset_code,
    template_name='emailauth/reset_password.html'):

    user_email = get_object_or_404(UserEmail, verification_key=reset_code)
    if (user_email.verification_key == UserEmail.VERIFIED or
        user_email.code_creation_date +
        timedelta(days=email_verification_days()) < datetime.now()):

        raise Http404()

    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            user = user_email.user
            user.set_password(form.cleaned_data['password1'])
            user.save()

            user_email.verification_key = UserEmail.VERIFIED
            user_email.save()

            from django.contrib.auth import login
            user.backend = 'emailauth.backends.EmailBackend'
            login(request, user)
            return HttpResponseRedirect(reverse('emailauth_account'))
    else:
        form = PasswordResetForm()

    context = RequestContext(request)
    return render_to_response(template_name,
        {'form': form},
        context_instance=context)


@requires_multi_emails_mode
@login_required
def add_email(request, template_name='emailauth/add_email.html'):
    if request.method == 'POST':
        form = AddEmailForm(request.POST)
        if form.is_valid():
            email_obj = UserEmail.objects.create_unverified_email(
                form.cleaned_data['email'], user=request.user)
            email_obj.send_verification_email()
            email_obj.save()
            return HttpResponseRedirect(reverse('emailauth_add_email_continue',
                args=[email_obj.email]))
    else:
        form = AddEmailForm()

    context = RequestContext(request)
    return render_to_response(template_name,
        {'form': form},
        context_instance=context)


@requires_multi_emails_mode
@login_required
def add_email_continue(request, email,
    template_name='emailauth/add_email_continue.html'):

    return render_to_response(template_name,
        {'email': email},
        context_instance=RequestContext(request))


@requires_single_email_mode
@login_required
def change_email(request, template_name='emailauth/change_email.html'):
    if request.method == 'POST':
        form = AddEmailForm(request.POST)
        if form.is_valid():
            UserEmail.objects.filter(user=request.user, default=False).delete()

            email_obj = UserEmail.objects.create_unverified_email(
                form.cleaned_data['email'], user=request.user)
            email_obj.send_verification_email()
            email_obj.save()

            return HttpResponseRedirect(reverse('emailauth_change_email_continue',
                args=[email_obj.email]))
    else:
        form = AddEmailForm()

    context = RequestContext(request)
    return render_to_response(template_name,
        {'form': form},
        context_instance=context)


@requires_single_email_mode
@login_required
def change_email_continue(request, email,
    template_name='emailauth/change_email_continue.html'):

    return render_to_response(template_name,
        {'email': email},
        context_instance=RequestContext(request))


@requires_multi_emails_mode
@login_required
def delete_email(request, email_id,
    template_name='emailauth/delete_email.html'):

    user_email = get_object_or_404(UserEmail, id=email_id, user=request.user,
        verified=True)

    if request.method == 'POST':
        form = DeleteEmailForm(request.user, request.POST)
        if form.is_valid():
            user_email.delete()

            # Not really sure, where I should redirect from here...
            return HttpResponseRedirect(reverse('emailauth_account'))
    else:
        form = DeleteEmailForm(request.user)

    context = RequestContext(request)
    return render_to_response(template_name,
        {'form': form, 'email': user_email},
        context_instance=context)


@requires_multi_emails_mode
@login_required
def set_default_email(request, email_id,
    template_name='emailauth/set_default_email.html'):

    user_email = get_object_or_404(UserEmail, id=email_id, user=request.user,
        verified=True)

    if request.method == 'POST':
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            user_email.default = True
            user_email.save()
            return HttpResponseRedirect(reverse('emailauth_account'))
    else:
        form = ConfirmationForm()

    context = RequestContext(request)
    return render_to_response(template_name,
        {'form': form, 'email': user_email},
        context_instance=context)
