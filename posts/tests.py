from io import BytesIO

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from posts.models import Follow, Group, Post, User


def make_post_with_image(self, just_image=False):
    container_for_img = BytesIO()
    img = Image.new("RGB", (100, 100), "red")
    img.save(container_for_img, format="JPEG")
    bin_image = container_for_img.getvalue()
    img = SimpleUploadedFile(
        name="test_image.jpg", content=bin_image, content_type="image/jpg"
    )
    if just_image:
        return img
    post = Post.objects.create(
        author=self.user, text="testtext", image=img, group=self.group
    )
    return post


class TestPostsApp(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mytestuser", "test@test.ru", "mytestpass")
        self.group = Group.objects.create(
            slug="testslug", title="mytestgroup", description="testdescr"
        )
        self.post = Post.objects.create(
            text="MyTestText", author=self.user, group=self.group
        )

        self.cl = Client()
        self.cl_auth = Client()
        self.cl_auth.force_login(self.user)

        cache.clear()

    def test_profile_page(self):
        response = self.cl.get(reverse("profile", kwargs={"username": "mytestuser"}))
        self.assertEqual(response.status_code, 200)

    def test_createpost_auth(self):
        img = make_post_with_image(self, just_image=True)
        response = self.cl_auth.post(
            reverse("new_post"),
            {"text": "MyTestText2", "image": img},
            follow=True,
        )
        image_in_post = response.context["page"].object_list[0].image
        self.assertTrue(image_in_post)

    def test_createpost_guest(self):
        response = self.cl.post(
            reverse("new_post"),
            {"text": "MyTestText"},
        )
        self.assertRedirects(response, reverse("login") + "?next=/new/")

    def test_newpost_index(self):
        response = self.cl.get(reverse("index"))
        self.assertContains(response, self.post)

    def test_newpost_profile(self):
        response = self.cl.get(reverse("profile", kwargs={"username": "mytestuser"}))
        self.assertContains(response, self.post)

    def test_newpost_post(self):
        response = self.cl.get(
            reverse("post", kwargs={"username": "mytestuser", "post_id": 1})
        )
        self.assertContains(response, self.post)

    def test_can_edit_post(self):
        response = self.cl_auth.post(
            reverse("post_edit", kwargs={"username": "mytestuser", "post_id": 1}),
            {"text": "MyTestText2"},
        )
        self.post = Post.objects.get(id=1)
        self.assertEqual(self.post.text, "MyTestText2")

    def test_editpost_index(self):
        self.post.text = "MyTestText2"
        self.post.save()
        response = self.cl.get(reverse("index"))
        self.assertContains(response, self.post.text)

    def test_editpost_profile(self):
        self.post.text = "MyTestText2"
        self.post.save()
        response = self.cl.get(reverse("profile", kwargs={"username": "mytestuser"}))
        self.assertContains(response, self.post.text)

    def test_editpost_post(self):
        self.post.text = "MyTestText2"
        self.post.save()
        response = self.cl.get(
            reverse("post", kwargs={"username": "mytestuser", "post_id": 1})
        )
        self.assertContains(response, self.post.text)

    def test_raise_404(self):
        response = self.cl.get(
            reverse("profile", kwargs={"username": "nosuchuser"}), follow=True
        )
        self.assertEqual(response.status_code, 404)

    def test_postpage_with_image(self):
        post = make_post_with_image(self)
        response = self.cl.get(
            reverse(
                "post",
                kwargs={"username": "mytestuser", "post_id": post.id},
            )
        )
        self.assertIn("img", response.content.decode())

    def test_indexpage_with_image(self):
        make_post_with_image(self)
        response = self.cl.get(reverse("index"))
        self.assertIn("img", response.content.decode())

    def test_profilepage_with_image(self):
        make_post_with_image(self)
        response = self.cl.get(reverse("profile", kwargs={"username": "mytestuser"}))
        self.assertIn("img", response.content.decode())

    def test_grouppage_with_image(self):
        make_post_with_image(self)
        response = self.cl.get(reverse("group", kwargs={"slug": "testslug"}))
        self.assertIn("img", response.content.decode())

    def test_upload_not_image(self):
        text_file = SimpleUploadedFile(
            name="textfile.txt",
            content=b"TestTextInFile",
        )
        response = self.cl_auth.post(
            reverse(
                "post_edit",
                kwargs={"username": "mytestuser", "post_id": self.post.id},
            ),
            {
                "text": "PostWithTextFile",
                "image": text_file,
                "group": self.group.pk,
            },
        )
        error_mesage = (
            "Загрузите правильное изображение. Файл, который вы загрузили, "
            "поврежден или не является изображением."
        )
        self.assertFormError(
            response,
            "form",
            "image",
            errors=error_mesage,
        )

    def test_auth_user_follow(self):
        author = User.objects.create_user("seconduser", "su@test.ru", "seconduserpass")
        self.cl_auth.post(reverse("profile_follow", kwargs={"username": "seconduser"}))

        self.assertTrue(
            Follow.objects.filter(author=author, user=self.user).exists(),
            msg="Subscribe doesn't exist",
        )

    def test_auth_user_unfollow(self):
        author = User.objects.create_user("seconduser", "su@test.ru", "seconduserpass")
        Follow.objects.create(author=author, user=self.user)

        self.cl_auth.post(
            reverse("profile_unfollow", kwargs={"username": "seconduser"})
        )
        self.assertFalse(
            Follow.objects.filter(author=author, user=self.user).exists(),
            msg="Subscribe hasn't deleted",
        )

    def test_follower_sees_post(self):
        author = User.objects.create_user("seconduser", "su@test.ru", "seconduserpass")
        author_post = Post.objects.create(text="testtext", author=author)

        Follow.objects.create(author=author, user=self.user)
        follower_response = self.cl_auth.get(reverse("follow_index"))
        self.assertContains(follower_response, author_post)

    def test_not_follower_sees_post(self):
        author = User.objects.create_user("seconduser", "su@test.ru", "seconduserpass")
        author_post = Post.objects.create(text="testtext", author=author)

        not_follower_response = self.cl_auth.get(reverse("follow_index"))
        self.assertNotContains(not_follower_response, author_post)

    def test_guest_cant_comment(self):
        response = self.cl.post(
            reverse(
                "add_comment",
                kwargs={"username": "mytestuser", "post_id": self.post.id},
            ),
            {"text": "TestComment"},
            follow=True,
        )
        self.assertFalse(self.post.comments.exists())

    def test_authuser_can_comment(self):
        response = self.cl_auth.post(
            reverse("add_comment", kwargs={"username": "mytestuser", "post_id": 1}),
            {"text": "TestComment"},
            follow=True,
        )
        self.assertTrue(self.post.comments.exists())


class TestCache(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mytestuser", "test@test.ru", "mytestpass")
        self.cl = Client()

    def test_post_in_index(self):
        resp = self.cl.get(reverse("index"))
        self.post = Post.objects.create(text="MyTestText111", author=self.user)
        resp = self.cl.get(reverse("index"))
        self.assertNotContains(
            resp,
            "MyTestText111",
            msg_prefix="Cache is not working, created post on index page",
        )
