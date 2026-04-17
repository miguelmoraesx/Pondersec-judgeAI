from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from . import views


@login_required
def comparador_view(request):
    return render(request,'comparador.html')
