from datetime import datetime as dt
from itertools import chain
from operator import attrgetter

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import cache_page

from posts.forms import CommentForm, NewPostForm
from posts.models import Comment, Follow, Group, Post, User

# Идея казалась хорошей, пока я не воплотил её
# в какого-то монстра Франкенштейна.
# Даже не знаю как это исправить.
# Извиняюсь за никакой английский.
def make_context(**kwargs):
    """ Can use this function to make additional context.
    
    Function returns dict "another_context", values of this dict
    are different objects for make context.

    Available keyword arguments:

    post - available value only is Post object. Will write to
    dictionary all comments and number of comments.
    
    count_author_posts - boolean. If True, then "author" argument is
    required. Author argument must be an object of model "Author". Will
    write to dictionary number posts by author.

    count_comments - available value any iterable object with Post 
    model objects inside. Will write to dictionary number comments of
    each post.

    is_editable - boolean. If True, then arguments "author" and "user"
    required. Will write to dictionary boolean type, if True its mean
    user is the author and he can edit post.

    is_following - boolean. If True, then arguments "author" and "user"
    required. Will write to dictionary boolean type, if True its mean
    user is already has a subscription to author.

    count_followings - boolean. If True, then argument "author" is
    required. Will write to dictionary 2 records, first with number of
    followings, second with number of followers.

    """
    another_context = {}
    if "post" in kwargs:
        post = kwargs["post"]
        post_comments = post.comments.all()
        post_comments_cnt = post.comments.count()
        another_context["post_comments"] = post_comments
        another_context["post_comments_cnt"] = post_comments_cnt

    if "count_author_posts" in kwargs:
        author = kwargs["author"]
        author_posts_cnt = author.posts.count()
        another_context["author_posts_cnt"] = author_posts_cnt

    if "count_comments" in kwargs:
        posts = kwargs["count_comments"]
        all_comments = (
            Comment.objects.values("post")
            .filter(post__in=posts)
            .annotate(total=Count("id"))
        )
        total_comments = {}
        for post_comments in all_comments:
            total_comments[post_comments["post"]] = post_comments["total"]

        another_context["total_comments"] = total_comments

    if "is_editable" in kwargs:
        user = kwargs["user"]
        author = kwargs["author"]
        can_edit = bool(user.is_authenticated and user == author)
        another_context["editable"] = can_edit

    if "is_following" in kwargs:
        user = kwargs["user"]
        author = kwargs["author"]
        following = bool(
            user.is_authenticated
            and Follow.objects.filter(author=author, user=user).exists()
        )
        another_context["following"] = following

    if "count_followings" in kwargs:
        author = kwargs["author"]
        following = author.following.count()
        follower = author.follower.count()
        another_context["following_count"] = following
        another_context["follower_count"] = follower

    return another_context


@cache_page(20, key_prefix="index_page")
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    additional_context = make_context(count_comments=page)
    return render(
        request,
        "index.html",
        {
            "page": page,
            "paginator": paginator,
            "additional_context": additional_context,
        },
    )


@login_required
def follow_index(request):
    favorites_authors_posts = Post.objects.filter(
        author__following__user=request.user
    )

    paginator = Paginator(favorites_authors_posts, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    additional_context = make_context(count_comments=page)

    return render(
        request,
        "follow_index.html",
        {
            "page": page,
            "paginator": paginator,
            "additional_context": additional_context,
        },
    )


def profile(request, username):
    author = get_object_or_404(User, username=username)
    author_posts = author.posts.all()
    paginator = Paginator(author_posts, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    additional_context = make_context(
        count_followings=True,
        count_author_posts=True,
        is_following=True,
        is_editable=True,
        user=request.user,
        author=author,
        count_comments=page,
    )
    return render(
        request,
        "profile.html",
        {
            "page": page,
            "paginator": paginator,
            "author": author,
            "additional_context": additional_context,
        },
    )


def post_view(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, id=post_id)
    author_posts_cnt = post.author.posts.count()
    comment_form = CommentForm()
    # Pytest хочет комментарии.
    comments = post.comments.all()
    additional_context = make_context(
        count_followings=True,
        count_author_posts=True,
        is_following=True,
        is_editable=True,
        post=post,
        author=post.author,
        user=request.user,
    )
    return render(
        request,
        "post.html",
        {
            "post": post,
            "comments": comments,
            "author": post.author,
            "form": comment_form,
            "additional_context": additional_context,
        },
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts_in_group = group.posts.all()
    paginator = Paginator(posts_in_group, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    additional_context = make_context(count_comments=page)
    return render(
        request,
        "group.html",
        {
            "page": page,
            "paginator": paginator,
            "group": group,
            "additional_context": additional_context,
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
