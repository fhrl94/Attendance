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
import xadmin
from django.conf.urls import url, include
from django.contrib import admin
from django.views.static import serve

from Attendance_Calculation.settings import CKEDITOR_UPLOAD_PATH

urlpatterns = [
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),
    url(r'^Attendance/', include('Attendance.urls')),
    url(r'^xadmin/', include(xadmin.site.urls)),
    url(r'^admin/', admin.site.urls),
    url(r'^{media_path}(?P<path>.*)'.format(media_path=CKEDITOR_UPLOAD_PATH), serve)
]
#  获取多媒体地址
