from datetime import datetime as dt
from itertools import chain
from operator import attrgetter

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import cache_page

from posts.forms import CommentForm, NewPostForm
from posts.models import Follow, Group, Post, User


def count_post_comments(page):
    comments_in_post = {}
    for post in page:
        comments_in_post[post.id] = post.comments.count()
    return comments_in_post


def count_follow(man):
    following = man.following.count()
    follower = man.follower.count()
    return following, follower


@cache_page(20, key_prefix="index_page")
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    each_post_comments = count_post_comments(page)
    return render(
        request,
        "index.html",
        {
            "page": page,
            "paginator": paginator,
            "each_post_comments": each_post_comments,
        },
    )


@login_required
def new_post(request):
    post_form = NewPostForm(request.POST or None, files=request.FILES or None)
    if post_form.is_valid():
        instance_form = post_form.save(commit=False)
        instance_form.author = request.user
        instance_form.save()
        return redirect("index")
    return render(request, "new_post.html", {"form": post_form})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    can_edit = bool(request.user.is_authenticated and request.user == author)
    author_posts = author.posts.all()
    paginator = Paginator(author_posts, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    each_post_comments = count_post_comments(page)
    follow = bool(
        request.user.is_authenticated
        and Follow.objects.filter(author=author, user=request.user).exists()
    )
    following_count, follower_count = count_follow(author)
    return render(
        request,
        "profile.html",
        {
            "page": page,
            "paginator": paginator,
            "can_edit": can_edit,
            "author": author,
            "each_post_comments": each_post_comments,
            "following": follow,
            "following_count": following_count,
            "follower_count": follower_count,
        },
    )


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


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts_in_group = group.posts.all()
    paginator = Paginator(posts_in_group, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    each_post_comments = count_post_comments(page)
    return render(
        request,
        "group.html",
        {
            "page": page,
            "paginator": paginator,
            "group": group,
            "each_post_comments": each_post_comments,
        },
    )


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


def post_view(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, id=post_id)
    author_posts_cnt = post.author.posts.count()
    can_edit = bool(
        request.user.is_authenticated and request.user == post.author
    )
    comment_form = CommentForm()
    post_comments = post.comments.all()
    post_comments_cnt = post.comments.count()
    follow = bool(
        request.user.is_authenticated
        and Follow.objects.filter(
            author=post.author, user=request.user
        ).exists()
    )
    following_count, follower_count = count_follow(post.author)
    return render(
        request,
        "post.html",
        {
            "can_edit": can_edit,
            "post": post,
            "author": post.author,
            "author_posts_cnt": author_posts_cnt,
            "form": comment_form,
            "post_comments": post_comments,
            "post_comments_cnt": post_comments_cnt,
            "following": follow,
            "following_count": following_count,
            "follower_count": follower_count,
        },
    )


@login_required
def follow_index(request):
    # Как же я долго искал это.... из-за него затянул весь спринт
    favorites_authors_posts = Post.objects.filter(
        author__following__user=request.user
    )

    paginator = Paginator(favorites_authors_posts, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    each_post_comments = count_post_comments(page)

    return render(
        request,
        "follow_index.html",
        {
            "page": page,
            "paginator": paginator,
            "each_post_comments": each_post_comments,
        },
    )


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    previous_page = request.META.get("HTTP_REFERER", "index")
    if author == request.user:
        return redirect(previous_page)
    if not Follow.objects.filter(user=request.user, author=author).exists():
        follow = Follow.objects.create(user=request.user, author=author)
    return redirect(previous_page)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    previous_page = request.META.get("HTTP_REFERER", "index")
    followings = Follow.objects.filter(user=request.user, author=author)
    if followings.exists():
        followings.delete()
    return redirect(previous_page)


def page_not_found(request, exception):
    return render(request, "misc/404.html", {"path": request.path}, status=404)


def server_error(request):
    return render(request, "misc/500.html", status=500)
