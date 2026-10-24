from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'), path('gallery/', views.gallery, name='gallery'),
    path('about/', views.about, name='about'), path('designs/<slug:slug>/', views.design, name='design'),
    path('photos/designs/<str:filename>', views.photo, name='photo'),
    path('subscribe/', views.subscribe, name='subscribe'), path('confirm/<str:token>/', views.confirm, name='confirm'),
    path('unsubscribe/<uuid:token>/', views.unsubscribe, name='unsubscribe'),
    path('owner/', views.owner, name='owner'), path('owner/login/', views.owner_login, name='owner_login'),
    path('owner/logout/', views.owner_logout, name='owner_logout'), path('owner/email-preview/', views.email_preview, name='email_preview'),
    path('privacy/', views.privacy, name='privacy'),
]
