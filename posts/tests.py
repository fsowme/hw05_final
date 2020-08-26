from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User


def upload_file_at_post_edit(browser, group, path_to_file):
    with open(path_to_file, "rb") as img:
        response = browser.post(
            reverse(
                "post_edit", kwargs={"username": "mytestuser", "post_id": 1},
            ),
            {"text": "post with image", "image": img, "group": group.pk},
            follow=True,
        )
        return response


class TestPostsApp(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username="mytestuser", password="mytestpass", email="test@test.ru"
        )
        self.group = Group.objects.create(
            slug="testslug", title="mytestgroup", description="testdescr"
        )
        self.post = Post.objects.create(
            text="MyTestText", author=self.user, group=self.group
        )
        self.cl = Client()
        self.cl_auth = Client()
        self.cl_auth.force_login(self.user)

    def test_profile_page(self):
        response = self.cl.get(
            reverse("profile", kwargs={"username": "mytestuser"})
        )
        self.assertEqual(response.status_code, 200)

    def test_createpost_auth(self):
        response = self.cl_auth.post(
            reverse("new_post"), {"text": "MyTestText2"}, follow=True
        )
        post_id = response.context["page"].object_list[0].id
        self.assertIn(
            Post.objects.get(id=post_id), Post.objects.all(),
        )

    def test_createpost_guest(self):
        response = self.cl.post(reverse("new_post"), {"text": "MyTestText"},)
        self.assertRedirects(response, reverse("login") + "?next=/new/")

    def test_newpost_index(self):
        response = self.cl.get(reverse("index"))
        self.assertContains(response, self.post)

    def test_newpost_profile(self):
        response = self.cl.get(
            reverse("profile", kwargs={"username": "mytestuser"})
        )
        self.assertContains(response, self.post)

    def test_newpost_post(self):
        response = self.cl.get(
            reverse("post", kwargs={"username": "mytestuser", "post_id": 1})
        )
        self.assertContains(response, self.post)

    def test_can_edit(self):
        response = self.cl_auth.post(
            reverse(
                "post_edit", kwargs={"username": "mytestuser", "post_id": 1}
            ),
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
        response = self.cl.get(
            reverse("profile", kwargs={"username": "mytestuser"})
        )
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
        file = "posts/files_on_test/test_image.jpg"
        upload_file_at_post_edit(self.cl_auth, self.group, file)
        response = self.cl.get(
            reverse("post", kwargs={"username": "mytestuser", "post_id": 1})
        )
        self.assertIn("img", response.content.decode())

    def test_indexpage_with_image(self):
        file = "posts/files_on_test/test_image.jpg"
        upload_file_at_post_edit(self.cl_auth, self.group, file)
        response = self.cl.get(reverse("index"))
        self.assertIn("img", response.content.decode())

    def test_profilepage_with_image(self):
        file = "posts/files_on_test/test_image.jpg"
        upload_file_at_post_edit(self.cl_auth, self.group, file)
        response = self.cl.get(
            reverse("profile", kwargs={"username": "mytestuser"})
        )
        self.assertIn("img", response.content.decode())

    def test_grouppage_with_image(self):
        file = "posts/files_on_test/test_image.jpg"
        upload_file_at_post_edit(self.cl_auth, self.group, file)
        response = self.cl.get(
            reverse("name_group", kwargs={"slug": "testslug"})
        )
        self.assertIn("img", response.content.decode())

    def test_upload_not_image(self):
        file = "posts/files_on_test/test_textfile.txt"
        response = upload_file_at_post_edit(self.cl_auth, self.group, file)
        self.assertIsNone(self.post.image.name)


class TestCache(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username="mytestuser", password="mytestpass", email="test@test.ru"
        )
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
        cache.clear()
        resp = self.cl.get(reverse("index"))
        self.assertContains(
            resp,
            "MyTestText111",
            msg_prefix="Created post is not on index page",
        )

    def test_1(self):
        self.cl.force_login(self.user)
        resp = self.cl.get(reverse("follow_index"))

        print(resp.context)
