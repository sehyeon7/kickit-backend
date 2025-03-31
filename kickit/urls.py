"""
URL configuration for kickit project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path, include
from django.http import HttpResponse, JsonResponse

def index(request):
    return HttpResponse("OK", status=200)

def apple_app_site_association(request):
    data = {
    "applinks": {
        "apps": [],
        "details": [
            {
                "appID": "5CH6LD5K2X.com.snulife.snulifeInternational",
                "paths": [
                    "*"
                ]
            }
        ]
    }
    }   
    return JsonResponse(data, content_type='application/json')

urlpatterns = [
    path('', index),
    path('admin/', admin.site.urls),
    path('account/', include('apps.account.urls')),
    path('board/', include('apps.board.urls')),
    path('notification/', include('apps.notification.urls')),
    path('settings/', include('apps.settings_app.urls')),
    path('.well-known/apple-app-site-association', apple_app_site_association),
]
