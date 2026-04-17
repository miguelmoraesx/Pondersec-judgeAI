from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [ 
    path('comparador/', views.comparador_view, name="comparador"),
]

 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 


