from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(File)
admin.site.register(Event)
admin.site.register(Solution)