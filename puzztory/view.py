from django.shortcuts import render
from PuzzModel.models import Fragment, UserExtension, Story, Announcement, Comment
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.core import serializers
import time
from datetime import date, datetime
import threading
import json
import math


index_dict = {
    'display': 'homepage',
    'story_list': '',
    'user_list': ''
}

experience_dict = {
    'upload_story': 20,
    'upload_frag': 5
}

# time allocated for user to add fragment: seconds
edit_time = 300
# 分页栏可视范围为(当前页-range，当前页+range)之外省略号...
paginator_view_range = 3
story_each_page = 10
frag_each_page = 10
message_each_page = 10
comment_each_page = 20

# frag_content_display_limit = 40
# comment_content_display_limit = 20
announce_content_limit = 35


class CJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        else:
            return json.JSONEncoder.default(self, obj)


def update_experience(request, type):
    current_user = UserExtension.objects.get(id=request.user.id)
    current_user.experience += experience_dict[type]
    current_user.level = math.floor(math.sqrt(round(current_user.experience / 5)))
    current_user.save()


def homepage(request):
    index_dict['display'] = 'homepage'
    index_dict['story_list'] = Story.objects.order_by('-likescount')[:5]
    index_dict['user_list'] = UserExtension.objects.order_by('-experience')[:5]

    # for Pagination
    story_full_list = Story.objects.order_by('-updatetime')
    paginator = Paginator(story_full_list, story_each_page)
    page = request.GET.get('page', 1)
    story_page_bound = {
        'left': int(page) - paginator_view_range,
        'right': int(page) + paginator_view_range
    }
    page_obj = paginator.get_page(page)

    if request.user.is_authenticated:
        message_count = len(Announcement.objects
                            .filter(touser=request.user.email, read=False)
                            .exclude(fromuser=request.user.email))
    else:
        message_count = 0
    index_dict['message_count'] = message_count

    index_dict['paginator'] = paginator
    index_dict['story_page_bound'] = story_page_bound
    index_dict['page_obj'] = page_obj
    index_dict['is_paginated'] = paginator.num_pages > 1
    return render(request, 'index.html', index_dict)


def messagejump(request, notification_id):
    announce = Announcement.objects.get(id=notification_id)
    optype = announce.optype
    targetid = announce.targetid
    # 跳转即已读：简单的实现
    announce.read = True
    announce.save()
    jump_to_frag = ['fraglike', 'addfrag', 'deletefrag', 'fragcomment']
    jump_to_comment = ['commentlike', 'cocomment', 'storycomment']
    if optype == 'storylike':
        return HttpResponseRedirect("/story/" + str(targetid))
    if optype in jump_to_frag:  
        story_id = Fragment.objects.get(id=targetid).storyid
        object_full_list = list(Fragment.objects.filter(storyid=story_id).order_by('createtime').values('id'))  
        location = object_full_list.index({'id': targetid})
        page = location // frag_each_page + 1
        append = str(story_id) + "?page=" + str(page) + \
        "&scroll_to_type_id=" + 'frag_' + str(targetid)
        return HttpResponseRedirect("/story/" + append)       
    elif optype in jump_to_comment:  
        story_id = Comment.objects.get(id=targetid).storyid
        comment_full_list = list(Comment.objects.filter(storyid=story_id).order_by('-createtime').values('id'))  
        location = comment_full_list.index({'id': targetid})
        page = location // comment_each_page + 1
        append = str(story_id) + "?comment_page=" + str(page) + \
        "&scroll_to_type_id=" + 'comment_' + str(targetid)
        return HttpResponseRedirect("/story/" + append)       


def storypage(request, story_id):
    frag_full_list = Fragment.objects.filter(
        storyid=story_id).order_by('createtime')   
    lastfrag_id = frag_full_list[len(frag_full_list)-1].id
    comment_full_list = Comment.objects.filter(
        sof=True, storyid=story_id).order_by('-createtime')

    paginator = Paginator(frag_full_list, frag_each_page)
    comment_paginator = Paginator(comment_full_list, comment_each_page)
    comment_page = request.GET.get('comment_page', -1) 
    # 区分是用户切换了评论页还是初次进入故事页
    # 如果是切换评论也需要滚动
    if comment_page == -1:
        comment_page = 1
        jump_page = False
    else:
        jump_page = True

    page = request.GET.get('page', -1)
    if page == -1:
        page = 1
        specific_page = False
    else:
        specific_page = True
    # scroll_to_type_id == -1 代表不需要片段滚动
    # 否则 scroll_to_type_id 代表滚动到的类型与对应的id号
    scroll_to_type_id = request.GET.get('scroll_to_type_id', -1)
    # 评论栏翻页，没有指定滚动到哪一条

    if jump_page and scroll_to_type_id == -1:
        scroll_to_type_id = 'commentscount'

    # 有滚动但是没有指定页或者 无法指定页 的情况
    # 这一块的逻辑有点糟糕但是其实知识一种特例,也不太要紧
    if scroll_to_type_id != -1 and scroll_to_type_id.startswith('frag') and not specific_page:
        object_full_list = list(Fragment.objects.filter(storyid=story_id).order_by('createtime').values('id'))
        location = object_full_list.index({'id': int(scroll_to_type_id[scroll_to_type_id.find('_') + 1:])})
        page = location // frag_each_page + 1

    # 翻页栏省略显示
    frag_page_bound = {
        'left': int(page) - paginator_view_range,
        'right': int(page) + paginator_view_range
    }

    comment_page_bound = {
        'left': int(comment_page) - paginator_view_range,
        'right': int(comment_page) + paginator_view_range
    }
    finished_message = request.GET.get('alreadyfinished', False)

    page_obj = paginator.page(page)
    comment_page_obj = comment_paginator.page(comment_page)
    comment_start_index = comment_paginator.count - (comment_page_obj.number - 1) * comment_each_page

    frag_like_list = []
    comment_like_list = []
    story_like = 'false'

    if request.user.is_authenticated:
        # 获得片段的点赞情况
        for frag in page_obj.object_list:
            try:
                Announcement.objects.get(
                    optype='fraglike', targetid=frag.id, fromuser=request.user.email)
                frag_like_list.append(frag.id)
            except Announcement.DoesNotExist:
                pass
        # 获得故事的点赞情况
        try:
            Announcement.objects.get(
                optype='storylike', targetid=story_id, fromuser=request.user.email)
            story_like = 'true'
        except Announcement.DoesNotExist:
            story_like = 'false'
        # 获得评论的点赞情况
        for comment in comment_page_obj.object_list:
            try:
                Announcement.objects.get(
                    optype='commentlike', targetid=comment.id, fromuser=request.user.email)
                comment_like_list.append(comment.id)
            except Announcement.DoesNotExist:
                pass

    if request.user.is_authenticated:
        message_count = len(Announcement.objects
                            .filter(touser=request.user.email, read=False)
                            .exclude(fromuser=request.user.email))
    else:
        message_count = 0

    is_paginated = paginator.num_pages > 1
    comment_is_paginated = comment_paginator.num_pages > 1

    story_dict = {
        'story': Story.objects.get(id=story_id),
        'is_paginated': is_paginated,
        'paginator': paginator,
        'page_obj': page_obj,
        'frag_page_bound': frag_page_bound,
        'comment_is_paginated': comment_is_paginated,
        'comment_paginator': comment_paginator,
        'comment_page_obj': comment_page_obj,
        'comment_page_bound': comment_page_bound,
        'comment_start_index': comment_start_index,
        'scroll_to_type_id': scroll_to_type_id,
        'finished_message': bool(finished_message),
        'frag_like_list': frag_like_list,
        'comment_like_list': comment_like_list,
        'story_like': story_like,
        'lastfrag_id': lastfrag_id,
        'message_count': message_count,
    }

    story = Story.objects.get(id=story_id)
    if story.keywords:
        keywords = str(story.keywords[:-1]).split(sep=';', maxsplit=5)
        story_dict['keywords'] = keywords
    if story.rules:
        rules = str(story.rules[:-1]).split(sep=';', maxsplit=5)
        story_dict['rules'] = rules

    return render(request, 'story.html', story_dict)


def upload_story_page(request):
    index_dict['display'] = 'upload_story'
    index_dict['story_list'] = Story.objects.order_by('-likescount')[:5]
    index_dict['user_list'] = UserExtension.objects.order_by('-experience')[:5]
    # return render(request, 'index.html', index_dict)
    message_count = len(Announcement.objects
                        .filter(touser=request.user.email, read=False)
                        .exclude(fromuser=request.user.email))
    index_dict['message_count'] = message_count
    return render(request, 'upload_story.html', index_dict)


def deletefrag(request, frag_id, story_id):
    try:
        # frag_full_list = Fragment.objects.filter(storyid=story_id).order_by('createtime')   
        # lastfrag_id = frag_full_list[len(frag_full_list)-1].id

        frag_record = Fragment.objects.get(id=frag_id) 
        targetfrag_id = Fragment.objects.filter(storyid=story_id).order_by('-createtime')[1].id  
        story_record = Story.objects.get(id=story_id)
        story_record.fragscount -= 1
        story_record.save()
        if len(frag_record.content) > announce_content_limit:
            frag_record_content = frag_record.content[:announce_content_limit] + '...'
        else:
            frag_record_content = frag_record.content
        announce_content = '删除了你在故事『' + story_record.title + '』中的片段：\n' + frag_record_content
        announce = Announcement(optype='deletefrag', targetid=targetfrag_id,
                                fromuser=request.user.email,
                                fromnickname=request.user.userextension.nickname,
                                touser=frag_record.email, tonickname=frag_record.nickname,
                                content=announce_content)

        announce.save()
        announce_content = '删除了你的故事『' + story_record.title + '』中的片段：\n' + frag_record_content
        announce = Announcement(optype='deletefrag', targetid=targetfrag_id,
                                fromuser=request.user.email,
                                fromnickname=request.user.userextension.nickname,
                                touser=story_record.email, tonickname=story_record.nickname,
                                content=announce_content)
        announce.save()
        Announcement.objects.filter(optype='addfrag', targetid=frag_id).delete()
        try:
            Announcement.objects.filter(optype='deletefrag', targetid=frag_id).delete()
            Announcement.objects.filter(optype='fraglike', targetid=frag_id).delete()
            Announcement.objects.filter(optype='fragcomment', targetid=frag_id).delete()
        except Announcement.DoesNotExist:
            pass
            
        frag_record.delete()

    except Fragment.DoesNotExist:
        pass

    frag_full_list = Fragment.objects.filter(
        storyid=story_id).order_by('createtime')
    paginator = Paginator(frag_full_list, frag_each_page)
    num_pages = paginator.num_pages
    # 置 last_frag_id 为最后一页最后一个片段
    fraglist = paginator.page(num_pages).object_list
    location = len(fraglist) - 1 
    last_frag_id = fraglist[location].id
    append = str(story_id) + "?page=" + str(num_pages) + \
        "&scroll_to_type_id=" + 'frag_' + str(last_frag_id)
    return HttpResponseRedirect("/story/" + append)
    

def upload_frag(request, story_id):
    if request.method == 'POST':
        story_record = Story.objects.get(id=story_id)
        # 当用户提交片段时故事已被作者完结，返回故事首页并提示
        if story_record.finished:
            append = str(story_id) + "?alreadyfinished=" + str(True)
            return HttpResponseRedirect("/story/" + append)

        frag_text = request.POST['fcontent']
        last_frag = Fragment.objects.filter(storyid=story_id).order_by('-createtime')[0]

        frag_record = Fragment(
            content=frag_text, nickname=request.user.userextension.nickname,
            email=request.user.email, storyid=story_id)
        frag_record.save()
        story_record.fragscount += 1
        # unlock the story once the fragment is submitted
        # meanwhile refresh attribute editor, remains, updatetime
        story_record.lock = False
        story_record.remains = 0
        # story_record.updatetime = timezone.now
        story_record.updatetime = frag_record.createtime
        story_record.save()
        update_experience(request, 'upload_frag')

        if len(frag_text) > announce_content_limit:
            frag_text = frag_text[:announce_content_limit] + '...'
        fragm_text = '在你的故事『' + story_record.title + '』中接续：\n' + frag_text
        # 修改通知表
        announcement = Announcement(optype='addfrag', targetid=frag_record.id,
                                    fromuser=request.user.email,
                                    fromnickname=request.user.userextension.nickname,
                                    touser=story_record.email, tonickname=story_record.nickname,
                                    content=fragm_text)
        announcement.save()
        if len(last_frag.content) > announce_content_limit:
            last_frag_content = last_frag.content[:announce_content_limit] + '...'
        else:
            last_frag_content = last_frag.content
        fragm_text = '在你的片段：\n“' + last_frag_content + '” 下接续：\n' + frag_text
        announcement = Announcement(optype='addfrag', targetid=frag_record.id,
                                    fromuser=request.user.email,
                                    fromnickname=request.user.userextension.nickname,
                                    touser=last_frag.email, tonickname=last_frag.nickname,
                                    content=fragm_text)
        announcement.save()

    frag_full_list = Fragment.objects.filter(
        storyid=story_id).order_by('createtime')
    paginator = Paginator(frag_full_list, frag_each_page)
    # 置 last_frag_id 为当前页最后一个片段
    append = str(story_id) + "?page=" + str(paginator.num_pages) + \
        "&scroll_to_type_id=" + 'frag_' + str(frag_record.id)
    return HttpResponseRedirect("/story/" + append)


def submit_comment(request, story_id, page):
    append = ""
    if request.method == 'POST':
        comment_content = request.POST['content']
        # story_id = request.POST['story_id']
        # 被回复的评论ID
        comment_reply_id = request.POST['replyToCommentID']
        if comment_reply_id:
            comment_reply_id = comment_reply_id[str(comment_reply_id).find('_')+1:]
        comment = Comment(nickname=request.user.userextension.nickname,
                          email=request.user.email, sof=True, storyid=story_id,
                          content=comment_content)
        comment.save()
        story = Story.objects.get(id=story_id)
        if str(comment_content).startswith('>>No.') and comment_reply_id:
            reply_comment = Comment.objects.get(id=comment_reply_id)
            touser = reply_comment.email
            tonickname = reply_comment.nickname
            reply_comment_content = reply_comment.content
            # 原评论长度过长，缩略显示
            if len(reply_comment_content) > announce_content_limit:
                reply_comment_content = reply_comment_content[:announce_content_limit] + '...'
            # 在通知栏里就不显示“>>***”那部分了
            comment_content = comment_content[str(comment_content).find(' ')+1:]
            if len(comment_content) > announce_content_limit:
                comment_content = comment_content[:announce_content_limit] + '...'
            content = '在你的评论 “' + reply_comment_content + '” 下回复：\n' + comment_content
            announcement = Announcement(optype='cocomment', targetid=comment_reply_id,
                                        fromuser=request.user.email,
                                        fromnickname=request.user.userextension.nickname,
                                        touser=touser, tonickname=tonickname,
                                        content=content)
            announcement.save()                                            
        else:
            touser = story.email
            tonickname = story.nickname
            title = story.title
            content = '在你的故事『' + title + '』中评论：\n' + comment_content
            announcement = Announcement(optype='storycomment', targetid=comment.id,
                                        fromuser=request.user.email,
                                        fromnickname=request.user.userextension.nickname,
                                        touser=touser, tonickname=tonickname,
                                        content=content)
            announcement.save()
        story.commentscount += 1
        story.save()
        append = str(story_id) + "?page=" + str(page) + \
            "&scroll_to_type_id=" + 'comment_' + str(comment.id)
    return HttpResponseRedirect("/story/" + append)


def submit_frag_comment(request):
    ret_dict = {}
    ret_dict['comment'] = ''
    if request.method == 'POST':
        frag_id = request.POST['frag_id']
        content = request.POST['content']
        frag = Fragment.objects.get(id=frag_id)
        # 添加到评论表中
        comment = Comment(
            nickname=request.user.userextension.nickname, email=request.user.email,
            sof=False, fragid=frag_id, content=content
        )
        comment.save()
        frag.commentscount += 1
        frag.save()
        # 通知栏中不显示过长的内容
        if len(frag.content) > announce_content_limit:
            frag_content = frag.content[:announce_content_limit] + '...'
        else:
            frag_content = frag.content
        
        if len(content) > announce_content_limit:
            content = content[:announce_content_limit]
        notification_content = '在你的片段：\n“' + frag_content + '”下评论：\n' + content
        # 添加到通知表中
        announcement = Announcement(
            optype='fragcomment', targetid=frag_id, fromuser=request.user.email,
            fromnickname=request.user.userextension.nickname, touser=frag.email,
            tonickname=frag.nickname, content=notification_content
        )
        announcement.save()

        # 现在只发送一个片段（即刚发送的片段）
        comment = Comment.objects.filter(id=comment.id).values('nickname', 'content', 'createtime')
        comment = json.dumps(list(comment), cls=CJsonEncoder)
        ret_dict['comment'] = comment
    return JsonResponse(data=ret_dict)


# 点击按钮时把点击片段对应的所有评论发给前端
def show_frag_comment(request):
    ret_dict = {}
    ret_dict['comments'] = ''
    if request.method == 'POST':
        frag_id = request.POST['frag_id']
        comments = Comment.objects.filter(fragid=frag_id).order_by('-createtime').values('nickname', 'content', 'createtime')
        comments = json.dumps(list(comments), cls=CJsonEncoder)
        ret_dict['comments'] = comments
    return JsonResponse(data=ret_dict)


def upload_story(request):
    # keys in request.POST:
    # MUST HAVE: title, ffcontent
    # MAY HAVE: branch, modified -> 'on' if checkbox was checked
    # MAY HAVE: fragWordsLimit: the maximum number of words a fragment can have in current story
    # MAY HAVE: fragsCountLimit: the maximum number of fragments a story can have
    if request.method == 'POST':
        story_title = request.POST['title']
        first_frag_text = request.POST['ffcontent']
        frag_record = Fragment(
            content=first_frag_text, nickname=request.user.userextension.nickname,
            email=request.user.email, storyid=0)
        frag_record.save()

        keyword_list = ['Keyword1', 'Keyword2', 'Keyword3', 'Keyword4', 'Keyword5']
        keyword_str = ''
        rule_list = ['Rule1', 'Rule2', 'Rule3', 'Rule4', 'Rule5']
        rule_str = ''
        for keyword in keyword_list:
            if keyword in request.POST:
                user_keyword = str(request.POST[keyword]).replace(';', ' ')
                keyword_str += (user_keyword + ';')
        for rule in rule_list:
            if rule in request.POST:
                user_rule = str(request.POST[rule]).replace(';', ' ')
                rule_str += (user_rule + ';')
        if keyword_str == '':
            keyword_str = None
        if rule_str == '':
            rule_str = None

        story_record = Story(
            nickname=request.user.userextension.nickname, email=request.user.email,
            editor=request.user.email, title=story_title, ffid=frag_record.id, ffcontent=first_frag_text,
            keywords=keyword_str, rules=rule_str)

        if 'branch' in request.POST:
            story_record.branch = True
        if 'modified' not in request.POST:
            story_record.modified = False
        if 'fragWordsLimit' in request.POST:
            story_record.fragwordslimit = request.POST['fragWordsLimit']
        if 'fragsCountLimit' in request.POST:
            story_record.fragscountlimit = request.POST['fragsCountLimit']
        story_record.save()
        frag_record.storyid = story_record.id
        frag_record.save()
        update_experience(request, 'upload_story')

    return HttpResponseRedirect("/")


def system_message(request):
    index_dict['display'] = 'system_message'
    index_dict['story_list'] = Story.objects.order_by('-likescount')[:5]
    index_dict['user_list'] = UserExtension.objects.order_by('-experience')[:5]
    
    like_full_list = Announcement.objects.filter(
        optype__endswith='like', touser=request.user.email
    ).exclude(fromuser=request.user.email).order_by('-createtime')
    paginator = Paginator(like_full_list, message_each_page)
    likepage = request.GET.get('likepage', -1)
    if likepage != -1:
        index_dict['show'] = "likepage"
    else:
        likepage = 1

    index_dict['like_page_bound'] = {
        'left': int(likepage) - paginator_view_range,
        'right': int(likepage) + paginator_view_range
    }
    index_dict['like_page_obj'] = paginator.get_page(likepage)
    index_dict['like_paginator'] = paginator
    index_dict['like_is_paginated'] = paginator.num_pages > 1

    index_dict['unread_likes_count'] = len(like_full_list.exclude(read=True).values())


    fragnoti_full_list = Announcement.objects.filter(
        optype__endswith='frag', touser=request.user.email
    ).exclude(fromuser=request.user.email).order_by('-createtime')
    paginator = Paginator(fragnoti_full_list, message_each_page)
    fragpage = request.GET.get('fragpage', -1)
    if fragpage != -1:
        index_dict['show'] = "fragpage"
    else:
        fragpage = 1

    index_dict['frag_page_bound'] = {
        'left': int(fragpage) - paginator_view_range,
        'right': int(fragpage) + paginator_view_range
    }
    index_dict['frag_page_obj'] = paginator.get_page(fragpage)
    index_dict['frag_paginator'] = paginator
    index_dict['frag_is_paginated'] = paginator.num_pages > 1

    index_dict['unread_fragnoti_count'] = len(fragnoti_full_list.exclude(read=True).values())


    commentnoti_full_list = Announcement.objects.filter(
        optype__endswith='comment', touser=request.user.email
    ).exclude(fromuser=request.user.email).order_by('-createtime')
    message_count = len(Announcement.objects
                        .filter(touser=request.user.email, read=False)
                        .exclude(fromuser=request.user.email))
    index_dict['message_count'] = message_count
    paginator = Paginator(commentnoti_full_list, message_each_page)
    commentpage = request.GET.get('commentpage', -1)
    if commentpage != -1:
        index_dict['show'] = "commentpage"
    else:
        commentpage = 1

    index_dict['comment_page_bound'] = {
        'left': int(commentpage) - paginator_view_range,
        'right': int(commentpage) + paginator_view_range
    }
    index_dict['comment_page_obj'] = paginator.get_page(commentpage)
    index_dict['comment_paginator'] = paginator
    index_dict['comment_is_paginated'] = paginator.num_pages > 1

    index_dict['unread_commentnoti_count'] = len(commentnoti_full_list.exclude(read=True).values())

    return render(request, 'system_message.html', index_dict)


def login_page(request):
    login_dict = {
        'emailNotExistedAlert': "",
        'passwordIncorrect': "",
        'useremail': ""
    }
    return render(request, 'login.html', login_dict)


def register_page(request):
    register_dict = {
        'emailExistedAlert': ""
    }
    return render(request, 'register.html', register_dict)


def likescount(request):
    request_id = request.GET.get('id')
    liketype = request_id[str(request_id).find('_')+1:]
    request_id = request_id[:str(request_id).find('_')]
    ret_dict = {}
    if liketype == 'storylikescount':
        var_set = Story.objects
        optype = 'storylike'
        content = var_set.get(id=request_id).title

    elif liketype == 'fraglikescount':
        var_set = Fragment.objects
        optype = 'fraglike'
        content = var_set.get(id=request_id).content

    else:
        var_set = Comment.objects
        optype = 'commentlike'
        content = var_set.get(id=request_id).content

    var = var_set.get(id=request_id)
    if len(content) > announce_content_limit:
        content = content[:announce_content_limit] + '...'
    try:
        announce = Announcement.objects.get(
            optype=optype, targetid=request_id, fromuser=request.user.email)
        announce.delete()
        # var = var_set.get(id=request_id)
        var.likescount -= 1
        # ret_dict['count'] = var.likescount
        # var.save()
        ret_dict['message'] = 'delete'
    except Announcement.DoesNotExist:
        announce_record = Announcement(
            optype=optype, targetid=request_id, fromuser=request.user.email,
            fromnickname=request.user.userextension.nickname, touser=var.email, tonickname=var.nickname, content=content)
        
        announce_record.save()
        # var = var_set.get(id=request_id)
        var.likescount += 1
        # ret_dict['count'] = var.likescount
        # var.save()
        ret_dict['message'] = 'add'

    ret_dict['count'] = var.likescount
    var.save()
    return JsonResponse(data=ret_dict)


def modifiedset(request):
    request_id = request.GET.get('story_id')
    story = Story.objects.get(id=request_id)
    ret_dict = {}
    ret_dict['lock'] = story.lock

    if not story.lock:
        # 翻转操作
        ret_dict['modified'] = story.modified
        story.modified = not story.modified
        story.save()

    return JsonResponse(data=ret_dict)


def finishedset(request):
    request_id = request.GET.get('story_id')
    story = Story.objects.get(id=request_id)
    ret_dict = {}

    story.finished = True
    story.modified = True
    story.lock = False
    story.save()

    ret_dict['finished'] = True

    return JsonResponse(data=ret_dict)


def lock(request):
    request_id = request.GET.get('story_id')
    story = Story.objects.get(id=request_id)
    ret_dict = {}
    ret_dict['submittimelimit'] = edit_time
    ret_dict['countdown'] = True
    last_fragment = Fragment.objects.filter(storyid=request_id).order_by('-createtime')[0]
    if len(last_fragment.content) > 20:
        lfcontent_text = '...' + last_fragment.content[-20:]
    else:
        lfcontent_text = last_fragment.content
    ret_dict['lfcontent'] = lfcontent_text

    # if the author forbade this story from editting
    if not story.modified:
        if request.user.email != story.email:
            ret_dict['allowed'] = False
        else:
            ret_dict['allowed'] = True
            ret_dict['countdown'] = False
    else:
        if story.lock:
            # if the same user requests for the second time
            if request.user.email == story.editor:
                ret_dict['allowed'] = True
                ret_dict['submitcountdown'] = story.remains
            # if another user request arrives when it's locked
            else:
                ret_dict['allowed'] = False
        # if story is not locked and user request to edit this story
        else:
            story.lock = True
            story.editor = request.user.email
            story.remains = edit_time
            story.save()
            ret_dict['allowed'] = True
            ret_dict['submitcountdown'] = story.remains
            # a timer thread to release lock after edit_time:seconds
            args = [request_id]
            timer = threading.Timer(1, count_down, args)
            timer.start()
    return JsonResponse(data=ret_dict)


def count_down(request_id):
    # if the counting is not over
    story = Story.objects.get(id=request_id)
    if story.remains > 0:
        story.remains -= 1
        story.save()
        # start a new timer ever second
        args = [request_id]
        timer = threading.Timer(1, count_down, args)
        timer.start()
    # now the counting is over, unlock the story
    else:
        story = Story.objects.get(id=request_id)
        if story.lock:
            story.lock = False
        story.save()
