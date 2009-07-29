# -*- coding: utf-8 -*-
from django import template
from emailauth.forms import LoginForm

register = template.Library()

@register.inclusion_tag('emailauth/loginform.html', takes_context=True)
def loginform(context):
    form = LoginForm()
    user = context['request'].user
    return locals()