from PuzzModel.models import Fragment, UserExtension, Story, Announcement, Comment
from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.db import IntegrityError


def register(request):
    login_dict = {
        'emailNotExistedAlert': "",
        'passwordIncorrect': "",
        'useremail': ""
    }
    request.encoding = 'utf-8'
    if request.method == 'POST':
        user_email = request.POST['e']
        user_name = request.POST['u']
        pwd = request.POST['p']
        # successfully create new user
        register_dict = {}
        try:
            user = UserExtension.objects.create_user(
                username=user_email, email=user_email, password=pwd)
        except IntegrityError:
            register_dict['emailExistedAlert'] = "邮箱地址已被注册"
            return render(request, 'register.html', register_dict)
        user.nickname = user_name
        user.save()
        login_dict['useremail'] = user_email
    return render(request, 'login.html', login_dict)


def Login(request):
    login_dict = {
        'emailNotExistedAlert': "",
        'passwordIncorrect': "",
        'useremail': ""
    }
    request.encoding = 'utf-8'
    if request.method == 'POST':
        user_email = request.POST['e']
        pwd = request.POST['p']
        try:
            UserExtension.objects.get(email=user_email)
        except UserExtension.DoesNotExist:
            login_dict['emailNotExistedAlert'] = "该用户不存在"
            return render(request, "login.html", login_dict)
        user = authenticate(username=user_email, password=pwd)
        if user is None:
            login_dict['passwordIncorrect'] = "密码错误"
            return render(request, "login.html", login_dict)
        else:
            login(request, user)
            return HttpResponseRedirect("/")
    return render(request, "login.html", login_dict)


def Logout(request):
    # End session
    logout(request)
    # return to homepage
    return HttpResponseRedirect("/")


def userpage(request, id):
    '''
    生成用户个人空间页
    '''
    owner = UserExtension.objects.get(id=id)
    message_count = len(Announcement.objects
                        .filter(touser=request.user.email, read=False)
                        .exclude(fromuser=request.user.email))
    user_story_list = Story.objects.filter(email=owner.email).order_by('-createtime')
    user_frag_list = Fragment.objects.filter(email=owner.email).order_by('-createtime')
    experience_upper = 5 * pow(owner.level+1, 2)
    index_dict = {
        'display': 'user_space',
        'story_list': Story.objects.order_by('-likescount')[:5],
        'user_list': UserExtension.objects.order_by('-experience')[:5],
        'owner': owner,
        'experience_upper': experience_upper,
        'message_count': message_count,
        'user_story_list': user_story_list,
        'user_frag_list': user_frag_list
    }
    # 当时真的该设计外键的，哭了
    for frag in user_frag_list:
        story = Story.objects.get(id=frag.storyid)
        index_dict['story' + str(frag.storyid) + '_title'] = story.title
    return render(request, "user_space.html", index_dict)