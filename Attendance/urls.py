"""Attendance_Calculation URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url

from Attendance import views

urlpatterns = [
    # URL暴露了，确保有登录验证
    url(r'^form_select', views.form_select, name='form_select'),
    url(r'^login/', view=views.user_login, name='login'),
    url(r'^home/', view=views.home_form, name='home'),
    url(r'^change_pwd/', view=views.change_pwd, name='change_pwd'),
    url(r'^logout/', view=views.user_logout, name='logout'),
    url(r'^ajax_dict/$', views.ajax_dict, name='ajax_dict'),
    url(r'^', view=views.error_404, kwargs={'error_body': ''}, name='error_404'),
]
