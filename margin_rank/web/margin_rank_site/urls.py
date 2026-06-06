from django.urls import path

from rankings import views

urlpatterns = [
    path("", views.index, name="index"),
]
