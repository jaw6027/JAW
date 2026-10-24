from django.contrib import admin
from django.urls import path, include
from studio.views import owner_login

urlpatterns = [path('owner/manage/login/', owner_login), path('owner/manage/', admin.site.urls), path('', include('studio.urls'))]
