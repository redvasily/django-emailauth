# -*- coding: utf-8 -*-
from django.contrib import admin
from emailauth.models import UserEmail


class UserEmailAdmin(admin.ModelAdmin):
    model = UserEmail
    list_display = ['user', 'email', 'verified',]

try:
    admin.site.register(UserEmail, UserEmailAdmin)
except admin.sites.AlreadyRegistered:
    pass
