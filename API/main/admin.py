from django.contrib import admin
from .models import User, Server, Transaction, Task

# Register your models here.
admin.site.register(User)
admin.site.register(Server)
admin.site.register(Transaction)
admin.site.register(Task)