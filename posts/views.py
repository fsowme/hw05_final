from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.template import Context
from django.views.decorators.cache import cache_page

from posts.forms import CommentForm, NewPostForm
from posts.models import Comment, Follow, Group, Post, User

context = Context()

def make_paginator(request, posts, total_on_page):
    paginator = Paginator(posts, total_on_page)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return paginator, page


def count_comments_on_page(posts):
    all_comments = (
        Comment.objects.values("post")
        .filter(post__in=posts)
        .annotate(total=Count("id"))
    )
    total_comments = {}
    for post_comments in all_comments:
        total_comments[post_comments["post"]] = post_comments["total"]

    return {"comments_on_page": total_comments}


def count_followings(person):
    following = person.following.count()
    follower = person.follower.count()
    return {"following": following, "follower": follower}


def is_following(author, user):
    follow = bool(
        user.is_authenticated
        and Follow.objects.filter(author=author, user=user).exists()
    )
    return {"follow": follow}


def is_editable(author, user):
    editable = bool(user.is_authenticated and user == author)
    return {"can_edit": editable}


@cache_page(20, key_prefix="index_page")
def index(request):
    post_list = Post.objects.all()
    paginator, page = make_paginator(request, post_list, 10)
    context = {"page": page, "paginator": paginator}
    context.update(count_comments_on_page(page))

    return render(request, "index.html", context)


@login_required
def follow_index(request):
    favorites_authors_posts = Post.objects.filter(author__following__user=request.user)
    paginator, page = make_paginator(request, favorites_authors_posts, 10)
    context = {"page": page, "paginator": paginator}
    context.update(count_comments_on_page(page))

    return render(request, "follow_index.html", context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    author_posts = author.posts.all()
    paginator, page = make_paginator(request, author_posts, 10)
    context = {
        "author": author,
        "author_posts": author.posts.count(),
        "page": page,
        "paginator": paginator,
    }
    context.update(count_comments_on_page(page))
    context.update(count_followings(author))
    context.update(is_editable(author, request.user))
    context.update(is_following(author, request.user))

    return render(request, "profile.html", context)


def post_view(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, id=post_id)
    comment_form = CommentForm()
    context = {
        "author": post.author,
        "author_posts": post.author.posts.count(),
        "comments_cnt": post.comments.count(),
        "comments": post.comments.all(),
        "form": comment_form,
        "post": post,
    }
    context.update(count_followings(post.author))
    context.update(is_editable(post.author, request.user))
    context.update(is_following(post.author, request.user))

    return render(request, "post.html", context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts_in_group = group.posts.all()
    paginator, page = make_paginator(request, posts_in_group, 10)
    context = {"group": group, "page": page, "paginator": paginator}
    context.update(count_comments_on_page(page))

    return render(request, "group.html", context)


@login_required
def new_post(request):
    post_form = NewPostForm(request.POST or None, files=request.FILES or None)
    if post_form.is_valid():
        instance_form = post_form.save(commit=False)
        instance_form.author = request.user
        instance_form.save()
        return redirect("index")
    return render(request, "new_post.html", {"form": post_form})


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, id=post_id)
    post_form = NewPostForm(
        request.POST or None, files=request.FILES or None, instance=post
    )
    if request.user != post.author:
        return redirect("post", username=username, post_id=post_id)

    if post_form.is_valid():
        post_form.author = request.user
        post_form.save()
        return redirect("post", username=username, post_id=post_id)

    return render(request, "new_post.html", {"form": post_form, "post": post})


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, id=post_id)
    comment_form = CommentForm(request.POST or None)
    if comment_form.is_valid:
        instance_comment = comment_form.save(commit=False)
        instance_comment.post = post
        instance_comment.author = request.user
        instance_comment.save()
    return redirect("post", username=username, post_id=post_id)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    previous_page = request.META.get("HTTP_REFERER", "index")
    if author == request.user:
        return redirect(previous_page)
    Follow.objects.get_or_create(user=request.user, author=author)
    return redirect(previous_page)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    previous_page = request.META.get("HTTP_REFERER", "index")
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect(previous_page)


def page_not_found(request, exception):
    return render(request, "misc/404.html", {"path": request.path}, status=404)


def server_error(request):
    return render(request, "misc/500.html", status=500)
