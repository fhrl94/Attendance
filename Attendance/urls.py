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
from django.conf.urls import url, include
from django.contrib import admin

from Attendance import views

urlpatterns = [
    # URL暴露了，确保有登录验证
    url(r'^data_select', views.data_select, name='data_select'),
    url(r'^shift_swap_select', views.shift_swap_select, name='shift_swap_select'),
    url(r'^cal_attendance_select', views.cal_attendance_select, name='cal_attendance_select'),
]
