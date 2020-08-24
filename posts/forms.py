from django import forms
from django.contrib.auth import get_user_model
from django.forms import ModelForm

from .models import Group, Post, Comment


class NewPostForm(ModelForm):
    class Meta:
        model = Post
        fields = ["group", "text", "image"]
        labels = {
            "group": ("Группа"),
            "text": ("Текст"),
            "image": ("Изображение"),
        }
        help_texts = {
            "group": ("Можете выбрать раздел вашего поста"),
            "text": ("Поделитесь с нами своими мыслями"),
            "image": ("Можете прикрепить изображение к посту"),
        }

    def clean_group(self):
        data = self.cleaned_data["group"]
        if not data:
            return data
        avail_group = Group.objects.filter(title=data).exists()
        if avail_group is not True:
            raise forms.ValidationError("Такой группы еще нет",)
        return data


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        labels = {"text": "Комментария"}
        help_texts = {"text": "Введите текст комментария"}

