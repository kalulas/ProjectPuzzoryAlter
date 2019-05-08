"""puzztory URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from . import view, user, testdb

urlpatterns = [
    path('', view.homepage),
    re_path(r'^userlogin$', user.Login),
    re_path(r'^userregister$', user.register),
    re_path(r'^login.html$', view.login_page),
    re_path(r'^register.html$', view.register_page),
    re_path(r'^testdb$', testdb.testdb),  # edit
    path('admin/', admin.site.urls),
]