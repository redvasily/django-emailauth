from os.path import dirname, abspath, join

from django.shortcuts import render_to_response
from django import template
from django.contrib.markup.templatetags.markup import restructuredtext

def index(request):
    readme_file = join(dirname(dirname(abspath(__file__))), 'README.txt')
    raw_content = open(readme_file).read()
    try:
        content = restructuredtext(raw_content)
    except template.TemplateSyntaxError:
        content = u'<pre>' + raw_content + u'</pre>'
        
    return render_to_response('index.html', {'content': content})
