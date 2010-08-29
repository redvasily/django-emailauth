================================
Django user email authentication
================================


This is a Django application providing all essentials for authenticating users
based on email addresses instead of usernames.

This application can operate in a traditional one user - one email mode as
well as one user - many emails mode.

This application consists of:

* UserEmail model

* Views and forms:

  - Login;
  - Password reset;
  - Account management:

    - User registration and email confirmation;
    - Adding and removing emails to/from existing user accounts;
    - Changing default emails
    - Changing email (for single email mode)

* Authentication backends:

  - Email backend for authenticating users who has UserEmail object (regular
    site users);
  - Fallback backend for users without such objects (most likely that will be
    site administration)


Motivation for this application
-------------------------------

For some reason I was lucky to work on projects which required email-based
authentication, and one of these projects could benefit if users could have
several emails.

To solve basic authentication problem I quickly came up with this:
http://www.djangosnippets.org/snippets/74/

That trick works but it has several drawbacks:

* It breaks standard Django tests, so when you run python manage.py test on
  your project you'll have to filter out error messages from broken Django
  tests. Not good.

* Standard Django login view can't handle long (longer than 30 characters)
  email addresses.

* If you put email verification status and all such into UserProfile class you
  tie code working with emails to your project impairing code reuse.


To solve above problems I decided to create this application. It stores all
email-specific data into UserEmail model (verification code, code creation
date, verification status etc.) So this application manages all email-related
data, not messing with UserProfile and saves application user from reinventing
the wheel.


Example project
---------------

To see this application in action::

    cd emailauth/example
    python manage.py syncdb
    python manage.py runserver

Please bear in mind that all emails sent by example project are not actually
sent but printed to stdout instead.

To see how traditional one user - one email mode works::

    cd emailauth/example
    python manage.py syncdb
    python manage.py runserver --settings=settings_singleemail


Installation and configuration
------------------------------

Installation
~~~~~~~~~~~~

First you need to somehow obtain 'emailauth' package.

Place 'emailauth' directory somewhere on your PYHTONPATH, for example in your
project directory, next to your settings.py -- that's the same place where
``python manage.py startapp`` creates applications.

If you are using some kind of isolated environment, like virtualenv, you can
just perform a regular installation::

    python setup.py install

Or::
    
    pip install django-emailauth

Or::
    
    easy_install django-emailauth


Configuration
~~~~~~~~~~~~~

Now you need to make several changes to your settings.py

* Add ``'emailauth'`` to your ``INSTALLED_APPS``

* Plug emailauth's authentication backends::

    AUTHENTICATION_BACKENDS = (
        'emailauth.backends.EmailBackend',
        'emailauth.backends.FallbackBackend',
    )

* Configure ``LOGIN_REDIRECT_URL`` and ``LOGIN_URL``. Emailauth's default
  urls.py expects them to be like this::

    LOGIN_REDIRECT_URL = '/account/'
    LOGIN_URL = '/login/'

* Optionally change a life time of email verification codes by changing
  ``EMAILAUTH_VERIFICATION_DAYS`` (default value is 3).

* Optionally set ``EMAILAUTH_USE_SINGLE_EMAIL = False`` if you want to use
  emailauth in "multiple-emails mode".

Now include emailauth's urls.py from your site's urls.py. Of course you may opt
for not including whole emailauth.urls, and write your own configuration, but
if you decide to use the provided urls.py, it will look like this::

    urlpatterns = patterns('',
        (r'', include('emailauth.urls')),
    )


Maintenance
~~~~~~~~~~~

By default emailauth uses automatic maintenance - it deletes expired UserEmail
objects when a new unverified email is created.

If you for some reason want to deactivate it and perform such maintenance
manually you can do it:

* Set ``EMAILAUTH_USE_AUTOMAINTENANCE = False`` in settings.py

* Run ``cleanupemailauth`` management command when you want to perform the
  cleanup::
    
    python manage.py clenupemailauth


Template customization
~~~~~~~~~~~~~~~~~~~~~~

Emailauth comes with a set of templates that should get you started, however
they won't be integrated with your site's templates - they don't extend the
right template and use wrong block for main content.

Don't worry, it's very easy to fix. All emailauth's templates extend
``emailauth/base.html`` and use ``emailauth_content`` block for content, so all
you need, is to modify ``emailauth/base.html`` and make it extend right
template and place ``emailauth_content`` block into right block specifc to your
site.

For example if your site's main template is ``mybase.html`` and you place all
content into ``mycontent`` block, you need to make following
``emailauth/base.html``::

    {% extends "mybase.html" %}

    {% block mycontent %}
        {% block emailauth_content %}
        {% endblock %}
    {% endblock %}


That's all
~~~~~~~~~~

By this point, if you started a new project and followed all the above
instructions above you should have a working instance of emailauth application.

To test it, start a server::

    python manage.py runserver

And open a registration page in your browser:
``http://127.0.0.1:8000/register/`` - it should display a registration page.
