# Generated by Django 2.2.9 on 2020-08-29 12:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0006_follow"),
    ]

    operations = [
        migrations.AlterField(
            model_name="comment",
            name="created",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
