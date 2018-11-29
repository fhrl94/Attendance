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
import os

import xadmin
from django.conf.urls import url, include
from django.contrib import admin
from django.views.static import serve

from Attendance_Calculation import settings

urlpatterns = [
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),
    url(r'^Attendance/', include('Attendance.urls')),
    url(r'^xadmin/', include(xadmin.site.urls)),
    url(r'^admin/', admin.site.urls),
    #  获取富文本编辑的多媒体地址
    url(r'^media/uploads/(?P<path>.*)$', serve, kwargs={'document_root': settings.MEDIA_ROOT + os.sep+ settings.CKEDITOR_UPLOAD_PATH})
]
