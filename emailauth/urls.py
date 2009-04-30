from django.conf.urls.defaults import *

import emailauth.views

urlpatterns = patterns('',
    url(r'^account/$', 'emailauth.views.account', name='emailauth_account'),

    url(r'^register/$', 'emailauth.views.register',
        name='register'),

    url(r'^register/continue/(?P<email>.+)/$',
        'emailauth.views.register_continue',
        name='emailauth_register_continue'),

    url(r'^verify/(?P<verification_key>\w+)/$', 'emailauth.views.verify',
        name='emailauth_verify'),

    url(r'^resetpassword/$', 'emailauth.views.request_password_reset',
        name='emailauth_request_password_reset'),
    url(r'^resetpassword/continue/(?P<email>.+)/$',
        'emailauth.views.request_password_reset_continue',
        name='emailauth_request_password_reset_continue'),
    url(r'^resetpassword/(?P<reset_code>\w+)/$',
        'emailauth.views.reset_password', name='emailauth_reset_password'),

    url(r'^account/addemail/$', 'emailauth.views.add_email',
        name='emailauth_add_email'),
    url(r'^account/addemail/continue/(?P<email>.+)/$',
        'emailauth.views.add_email_continue',
        name='emailauth_add_email_continue'),

    url(r'^account/deleteemail/(\d+)/$', 'emailauth.views.delete_email',
        name='emailauth_delete_email'),

    url(r'^account/setdefaultemail/(\d+)/$',
        'emailauth.views.set_default_email',
        name='emailauth_set_default_email'),

    url(r'^login/$', 'emailauth.views.login', name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/',
        'template_name': 'logged_out.html'}, name='logout'),
)
