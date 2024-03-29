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
    path('', view.homepage, name="index"),
    path('userlogin', user.Login, name="login"),
    path('userregister', user.register, name="register"),
    path('login', view.login_page, name="login_page"),
    path('register', view.register_page, name="register_page"),
    path('logout', user.Logout, name="logout"),
    path('space/<id>', user.userpage, name="user_page"),
    path('getfragtitle', user.get_title_byid, name="get_frag_title"),
    path('resetnickname', user.reset_nickname, name="reset_nickname"),
    path('checkpassword', user.check_password, name="check_password"),
    path('resetpassword', user.reset_password, name="reset_password"),
    path('changedescription', user.change_description, name="change_description"),
    path('upload', view.upload_story_page, name="upload_story_page"),
    path('message', view.system_message, name="system_message"),
    path('uploading', view.upload_story, name="upload_story"),
    path('story/adding/<int:story_id>', view.upload_frag, name="upload_frag"),
    path('story/comment/<int:story_id>/<int:page>',
         view.submit_comment, name="submit_comment"),
    path('story/submit_frag_comment', view.submit_frag_comment,
         name="submit_frag_comment"),
    path('story/show_frag_comment', view.show_frag_comment,
         name="show_frag_comment"),
    path('story/<int:story_id>', view.storypage, name="story_page"),
    path('lock', view.lock, name="lock"),
    path('likescount', view.likescount, name="likescount"),
    path('modifiedset', view.modifiedset, name="modifiedset"),
    path('finishedset', view.finishedset, name="finishedset"),
    path('deletefrag/<int:frag_id>/<int:story_id>',
         view.deletefrag, name="deletefrag"),
    path('messagejump/<int:notification_id>', view.messagejump, name="messagejump"),
    path('admin/', admin.site.urls),
]
