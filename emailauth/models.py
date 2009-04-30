import datetime
import random

import django.core.mail

from django.db import models
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from django.template.loader import render_to_string

from django.utils.hashcompat import sha_constructor
from django.utils.translation import ugettext_lazy as _
import django.core.mail

from django.conf import settings

from emailauth.signals import email_created


class UserEmailManager(models.Manager):
    def make_random_key(self, email):
        salt = sha_constructor(str(random.random())).hexdigest()[:5]
        key = sha_constructor(salt + email).hexdigest()
        return key

    def create_unverified_email(self, email, user=None):
        email_obj = UserEmail(email=email, user=user, default=user is None,
            verification_key=self.make_random_key(email))
        email_created.send(sender=self.model, email=email_obj)
        return email_obj

    def verify(self, verification_key):
        try:
            email = self.get(verification_key=verification_key)
        except self.model.DoesNotExist:
            return None
        if not email.verification_key_expired():
            email.verification_key = self.model.VERIFIED
            email.verified = True
            email.save()
            return email


class UserEmail(models.Model):
    class Meta:
        verbose_name = _('user email')
        verbose_name_plural = _('user emails')

    VERIFIED = 'ALREADY_VERIFIED'

    objects = UserEmailManager()

    user = models.ForeignKey(User, null=True, blank=True, verbose_name=_('user'))
    default = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    verified = models.BooleanField(default=False)
    code_creation_date = models.DateTimeField(default=datetime.datetime.now)
    verification_key = models.CharField(_('verification key'), max_length=40)

    def __init__(self, *args, **kwds):
        super(UserEmail, self).__init__(*args, **kwds)
        self._original_default = self.default

    def __unicode__(self):
        return self.email

    def save(self, *args, **kwds):
        super(UserEmail, self).save(*args, **kwds)
        if self.default and not self._original_default:
            self.user.email = self.email
            self.user.save()
            for email in self.__class__.objects.filter(user=self.user):
                if email.id != self.id and email.default:
                    email.default = False
                    email.save()

    def make_new_key(self):
        self.verification_key = self.__class__.objects.make_random_key(
            self.email)
        self.code_creation_date = datetime.datetime.now()

    def send_verification_email(self, first_name=None):
        current_site = Site.objects.get_current()
        
        subject = render_to_string('emailauth/verification_email_subject.txt',
            {'site': current_site})
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())

        emails = set()
        if self.user is not None:
            for email in self.__class__.objects.filter(user=self.user):
                emails.add(email.email)
        emails.add(self.email)
        first_email = len(emails) == 1

        if first_name is None:
            first_name = self.user.first_name
        
        message = render_to_string('emailauth/verification_email.txt', {
            'verification_key': self.verification_key,
            'expiration_days': settings.EMAIL_VERIFICATION_DAYS,
            'site': current_site,
            'first_name': first_name,
            'first_email': first_email,
        })

        django.core.mail.send_mail(subject, message,
            settings.DEFAULT_FROM_EMAIL, [self.email])


    def verification_key_expired(self):
        expiration_date = datetime.timedelta(days=settings.EMAIL_VERIFICATION_DAYS)
        return (self.verification_key == self.VERIFIED or
            (self.code_creation_date + expiration_date <= datetime.datetime.now()))

    verification_key_expired.boolean = True
