import re
from datetime import datetime, timedelta

from django.test.client import Client
from django.test.testcases import TestCase
from django.core import mail
from django.contrib.auth.models import User
from django.conf import settings

from emailauth.models import UserEmail
from emailauth.utils import email_verification_days


class Status:
    OK = 200
    REDIRECT = 302
    NOT_FOUND = 404


class BaseTestCase(TestCase):
    def assertStatusCode(self, response, status_code=200):
        self.assertEqual(response.status_code, status_code)

    def checkSimplePage(self, path, params={}):
        client = Client()
        response = client.get(path, params)
        self.assertStatusCode(response)

    def createActiveUser(self, username='username', email='user@example.com',
        password='password'):

        user = User(username=username, email=email, is_active=True)
        user.first_name = 'John'
        user.set_password(password)
        user.save()

        user_email = UserEmail(user=user, email=email, verified=True,
            default=True, verification_key=UserEmail.VERIFIED)
        user_email.save()
        return user, user_email

    def getLoggedInClient(self, email='user@example.com', password='password'):
        client = Client()
        client.login(username=email, password=password)
        return client


class RegisterTest(BaseTestCase):
    def testRegisterGet(self):
        self.checkSimplePage('/register/')

    def testRegisterPost(self):
        client = Client()
        response = client.post('/register/', {
            'email': 'user@example.com',
            'first_name': 'John',
            'password1': 'password',
            'password2': 'password',
        })
        self.assertRedirects(response, '/register/continue/user%40example.com/')

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        addr_re = re.compile(r'.*http://.*?(/\S*/)', re.UNICODE | re.MULTILINE)
        verification_url = addr_re.search(email.body).groups()[0]

        response = client.get(verification_url)

        self.assertRedirects(response, '/account/')

        response = client.post('/login/', {
            'email': 'user@example.com',
            'password': 'password',
        })

        self.assertRedirects(response, '/account/')

        user = User.objects.get(email='user@example.com')
        self.assertEqual(user.first_name, 'John')

    def testRegisterSame(self):
        user, user_email = self.createActiveUser()
        client = Client()
        response = client.post('/register/', {
            'email': user_email.email,
            'first_name': 'John',
            'password1': 'password',
            'password2': 'password',
        })
        self.assertContains(response, 'This email is already taken')

        email_obj = UserEmail.objects.create_unverified_email(
            'user@example.org', user)
        email_obj.save()

        response = client.post('/register/', {
            'email': 'user@example.org',
            'first_name': 'John',
            'password1': 'password',
            'password2': 'password',
        })
        self.assertContains(response, 'This email is already taken')
        


class LoginTest(BaseTestCase):
    def testLoginGet(self):
        self.checkSimplePage('/login/')

    def testLoginFail(self):
        user, user_email = self.createActiveUser()
        client = Client()
        response = client.post('/login/', {
            'email': 'user@example.com',
            'password': 'wrongpassword',
        })
        self.assertStatusCode(response, Status.OK)


class PasswordResetTest(BaseTestCase):
    def prepare(self):
        user, user_email = self.createActiveUser() 

        client = Client()
        response = client.post('/resetpassword/', {
            'email': user_email.email,
        })

        self.assertRedirects(response,
            '/resetpassword/continue/user%40example.com/')

        email = mail.outbox[0]
        addr_re = re.compile(r'.*http://.*?(/\S*/)', re.UNICODE | re.MULTILINE)
        reset_url = addr_re.search(email.body).groups()[0]
        return reset_url, user_email


    def testPasswordReset(self):
        reset_url, user_email = self.prepare()
        client = Client()

        self.checkSimplePage(reset_url)

        response = client.post(reset_url, {
            'password1': 'newpassword',
            'password2': 'newpassword',
        })

        self.assertRedirects(response, '/account/')

        user = User.objects.get(email=user_email.email)
        self.assertTrue(user.check_password('newpassword'))

        response = client.get(reset_url)
        self.assertStatusCode(response, Status.NOT_FOUND)


    def testPasswordResetFail(self):
        reset_url, user_email = self.prepare()
        client = Client()
        user_email.verification_key = UserEmail.VERIFIED
        user_email.save()

        response = client.get(reset_url)
        self.assertStatusCode(response, Status.NOT_FOUND)


    def testPasswordResetFail2(self):
        reset_url, user_email = self.prepare()
        client = Client()
        user_email.code_creation_date = (datetime.now() -
            timedelta(days=email_verification_days() + 1))
        user_email.save()

        response = client.get(reset_url)
        self.assertStatusCode(response, Status.NOT_FOUND)


class TestAddEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()

    def testAddEmailGet(self):
        response = self.client.get('/account/addemail/')
        self.assertStatusCode(response, Status.OK)

    def testAddEmail(self):
        response = self.client.post('/account/addemail/', {
            'email': 'user@example.org',
        })
        self.assertRedirects(response, '/account/addemail/continue/user%40example.org/')

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        addr_re = re.compile(r'.*http://.*?(/\S*/)', re.UNICODE | re.MULTILINE)
        verification_url = addr_re.search(email.body).groups()[0]

        response = self.client.get(verification_url)

        self.assertRedirects(response, '/account/')

        client = Client()
        response = client.post('/login/', {
            'email': 'user@example.org',
            'password': 'password',
        })

        self.assertRedirects(response, '/account/')

    def testAddSameEmail(self):
        response = self.client.post('/account/addemail/', {
            'email': 'user@example.com',
        })
        self.assertStatusCode(response, Status.OK)

        response = self.client.post('/account/addemail/', {
           'email': 'user@example.org',
        })
        self.assertRedirects(response,
            '/account/addemail/continue/user%40example.org/')

        response = self.client.post('/account/addemail/', {
          'email': 'user@example.org',
        })
        self.assertStatusCode(response, Status.OK)


class TestDeleteEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()

    def testDeleteEmail(self):
        user = self.user
        user_email = UserEmail(user=user, email='email@example.org', verified=True,
            default=False, verification_key=UserEmail.VERIFIED)
        user_email.save()

        response = self.client.post('/account/deleteemail/%s/' % user_email.id, {
            'yes': 'yes',
        })

        self.assertRedirects(response, '/account/')

        user_emails = UserEmail.objects.filter(user=self.user)
        self.assertEqual(len(user_emails), 1)

        response = self.client.post('/account/deleteemail/%s/' % user_emails[0].id, {
            'yes': 'yes',
        })

        self.assertStatusCode(response, Status.OK)


class TestSetDefaultEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()

    def testSetDefaultEmailGet(self):
        response = self.client.get('/account/setdefaultemail/%s/' %
            self.user_email.id)
        self.assertStatusCode(response, Status.OK)

    def testSetDefaultEmail(self):
        user = self.user
        user_email = UserEmail(user=user, email='user@example.org', verified=True,
            default=False, verification_key=UserEmail.VERIFIED)
        user_email.save()

        response = self.client.post('/account/setdefaultemail/%s/' % user_email.id, {
            'yes': 'yes',
        })

        self.assertRedirects(response, '/account/')

        new_default_email = user_email.email

        for email in UserEmail.objects.filter():
            self.assertEqual(email.default, email.email == new_default_email)

        user = User.objects.get(id=self.user.id)
        self.assertEqual(user.email, new_default_email)

    def testSetDefaultUnverifiedEmail(self):
        user = self.user
        user_email = UserEmail(user=user, email='user@example.org', verified=False,
            default=False, verification_key=UserEmail.VERIFIED)
        user_email.save()

        response = self.client.post('/account/setdefaultemail/%s/' % user_email.id, {
            'yes': 'yes',
        })
        self.assertStatusCode(response, Status.NOT_FOUND)

class TestDeleteEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()

    def testDeleteEmail(self):
        user_email = UserEmail(user=self.user, email='user@example.org', verified=True,
            default=False, verification_key=UserEmail.VERIFIED)
        user_email.save()

        page_url = '/account/deleteemail/%s/' % user_email.id

        response = self.client.get(page_url)
        self.assertStatusCode(response, Status.OK)

        response = self.client.post(page_url, {'yes': 'yes'})
        self.assertRedirects(response, '/account/')

    def testDeleteUnverifiedEmail(self):
        user_email = UserEmail(user=self.user, email='user@example.org', verified=False,
            default=False, verification_key=UserEmail.VERIFIED)
        user_email.save()
        
        response = self.client.post('/account/deleteemail/%s/' % user_email.id, {
            'yes': 'yes',
        })
        self.assertStatusCode(response, Status.NOT_FOUND)


class TestAccountSingleEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()
        settings.EMAILAUTH_USE_SINGLE_EMAIL = True

    def tearDown(self):
        settings.EMAILAUTH_USE_SINGLE_EMAIL = False

    def testAccountGet(self):
        response = self.client.get('/account/')
        self.assertStatusCode(response, Status.OK)

class TestChangeEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()
        settings.EMAILAUTH_USE_SINGLE_EMAIL = True

    def tearDown(self):
        settings.EMAILAUTH_USE_SINGLE_EMAIL = False

    def testEmailChangeWrongMode(self):
        settings.EMAILAUTH_USE_SINGLE_EMAIL = False
        response = self.client.get('/account/changeemail/')
        self.assertStatusCode(response, Status.NOT_FOUND)

    def testEmailChange(self):
        response = self.client.get('/account/changeemail/')
        self.assertStatusCode(response, Status.OK)

        response = self.client.post('/account/changeemail/', {
            'email': 'user@example.org',
        })

        self.assertRedirects(response,
            '/account/changeemail/continue/user%40example.org/')

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        addr_re = re.compile(r'.*http://.*?(/\S*/)', re.UNICODE | re.MULTILINE)
        verification_url = addr_re.search(email.body).groups()[0]

        response = self.client.get(verification_url)

        self.assertRedirects(response, '/account/')

        client = Client()
        response = client.post('/login/', {
            'email': 'user@example.org',
            'password': 'password',
        })

        self.assertRedirects(response, '/account/')

        user = User.objects.get(id=self.user.id)
        self.assertEqual(user.email, 'user@example.org')

        client = Client()
        response = client.post('/login/', {
            'email': 'user@example.com',
            'password': 'password',
        })
        self.assertStatusCode(response, Status.OK)


class TestResendEmail(BaseTestCase):
    def setUp(self):
        self.user, self.user_email = self.createActiveUser()
        self.client = self.getLoggedInClient()

    def testResendEmail(self):
        user = self.user
        user_email = UserEmail(user=user, email='user@example.org', verified=False,
            default=False, verification_key='abcdef')
        user_email.save()

        response = self.client.get('/account/resendemail/%s/' % user_email.id)
        self.assertRedirects(response,
            '/account/addemail/continue/user%40example.org/')
        self.assertEqual(len(mail.outbox), 1)
        

class TestCleanup(BaseTestCase):
    def testCleanup(self):
        user1 = User(username='user1', email='user1@example.com', is_active=True)
        user1.save()

        old_enough = (datetime.now() - timedelta(days=email_verification_days() + 1))
        not_old_enough = (datetime.now() -
            timedelta(days=email_verification_days() - 1))

        email1 = UserEmail(user=user1, email='user1@example.com',
            verified=True, default=True, 
            verification_key=UserEmail.VERIFIED + 'asd',
            code_creation_date=old_enough)
        email1.save() 

        user2 = User(username='user2', email='user2@example.com', is_active=False)
        user2.save()

        email2 = UserEmail(user=user2, email='user2@example.com',
            verified=False, default=True, 
            verification_key='key1',
            code_creation_date=old_enough)
        email2.save()

        user3 = User(username='user3', email='user3@example.com', is_active=False)
        user3.save()

        email3 = UserEmail(user=user3, email='user3@example.com',
            verified=False, default=True, 
            verification_key='key2',
            code_creation_date=not_old_enough)
        email3.save()

        UserEmail.objects.delete_expired()

        user_ids = [user.id for user in User.objects.all()]
        user_email_ids = [user_email.id for user_email in UserEmail.objects.all()]

        self.assertEqual(list(sorted(user_ids)), list(sorted([user1.id, user3.id])))
        self.assertEqual(list(sorted(user_email_ids)), list(sorted([email1.id, email3.id])))
