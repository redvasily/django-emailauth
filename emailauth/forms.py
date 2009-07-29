from django import forms
from django.contrib.auth import authenticate
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth.models import User

from emailauth.models import UserEmail

attrs_dict = {}

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict)))
    password = forms.CharField(widget=forms.PasswordInput(attrs=dict(attrs_dict),
        render_value=False))

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_("Please enter a correct email and "
                    "password. Note that both fields are case-sensitive."))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This account is inactive."))

        return self.cleaned_data

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache


def get_max_length(model, field_name):
    field = model._meta.get_field_by_name(field_name)[0]
    return field.max_length


def clean_password2(self):
    data = self.cleaned_data
    if 'password1' in data and 'password2' in data:
        if data['password1'] != data['password2']:
            raise forms.ValidationError(_(
                u'You must type the same password each time.'))
    if 'password2' in data:
        return data['password2']


class RegistrationForm(forms.Form):
    email = forms.EmailField(label=_(u'email address'))
    first_name = forms.CharField(label=_(u'first name'),
        max_length=get_max_length(User, 'first_name'),
        help_text=_(u"That's how we'll call you in emails"))
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_(u'password'))
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_(u'password (again)'))
    
    clean_password2 = clean_password2

    def clean_email(self):
        email = self.cleaned_data['email']

        try:
            user = UserEmail.objects.get(email=email)
            raise forms.ValidationError(_(u'This email is already taken.'))
        except UserEmail.DoesNotExist:
            pass
        return email
        

    def save(self):
        data = self.cleaned_data
        user = User()
        user.email = data['email']
        user.first_name = data['name']
        user.set_password(data['password1'])
        user.save()

        desired_username = 'id_%d_%s' % (user.id, user.email)
        user.username = desired_username[:get_max_length(User, 'username')]
        user.is_active = False
        user.save()
        
        registration_profile = (
            RegistrationProfile.objects.create_inactive_profile(user))
        registration_profile.save()

        profile = Account()
        profile.user = user
        profile.save()

        return user, registration_profile


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label=_(u'your email address'))

    def clean_email(self):
        data = self.cleaned_data
        try:
            user_email = UserEmail.objects.get(email=data['email'])
            return data['email']
        except UserEmail.DoesNotExist:
            raise forms.ValidationError(_(u'Unknown email'))


class PasswordResetForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_(u'password'))
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_(u'password (again)'))
    
    clean_password2 = clean_password2


class AddEmailForm(forms.Form):
    email = forms.EmailField(label=_(u'new email address'))

    def clean_email(self):
        email = self.cleaned_data['email']

        try:
            user = UserEmail.objects.get(email=email)
            raise forms.ValidationError(_(u'This email is already taken.'))
        except UserEmail.DoesNotExist:
            pass
        return email


class DeleteEmailForm(forms.Form):
    yes = forms.BooleanField(required=True)

    def __init__(self, user, *args, **kwds):
        self.user = user
        super(DeleteEmailForm, self).__init__(*args, **kwds)

    def clean(self):
        count = UserEmail.objects.filter(user=self.user).count()
        if UserEmail.objects.filter(user=self.user, verified=True).count() < 2:
            raise forms.ValidationError(_('You can not delete your last verified '
                'email.'))
        return self.cleaned_data


class ConfirmationForm(forms.Form):
    yes = forms.BooleanField(required=True)
