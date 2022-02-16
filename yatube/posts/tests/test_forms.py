import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from ..models import Post, Group
from ..utils import (
    get_urls_info,
    get_reversed_names
)

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group
        )

        cls.urls_info = get_urls_info(
            cls.user.username,
            cls.group.slug,
            cls.post.id
        )
        cls.reversed_pages_names = get_reversed_names(
            cls.urls_info
        )

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user)

    def test_create_post_form(self):
        """Валидная форма создает новый пост."""

        form_data = {
            'text': 'Тестовый текст нового поста'
        }
        response = self.authorized_client.post(
            PostFormTests.reversed_pages_names['posts:post_create'],
            data=form_data,
            follow=True
        )
        last_post = Post.objects.all().order_by('-id')[0]
        expected_values = {
            last_post.text: form_data['text'],
            last_post.author: PostFormTests.user
        }

        for value, expected in expected_values.items():
            with self.subTest(value=value):
                self.assertEqual(value, expected)

        redirect = PostFormTests.reversed_pages_names['posts:profile']
        self.assertRedirects(response, redirect)

    def test_create_post_with_group_and_image_form(self):

        form_data = {
            'text': 'Тестовый текст нового поста c группой',
            'group': PostFormTests.group.pk,
            'image': PostFormTests.uploaded
        }
        response = self.authorized_client.post(
            PostFormTests.reversed_pages_names['posts:post_create'],
            data=form_data,
            follow=True
        )

        last_post = Post.objects.all().order_by('-id')[0]
        expected_values = {
            last_post.text: form_data['text'],
            last_post.author: PostFormTests.user,
            last_post.group: PostFormTests.group,
            last_post.image: 'posts/small.gif'
        }

        for value, expected in expected_values.items():
            with self.subTest(value=value):
                self.assertEqual(value, expected)

        redirect = PostFormTests.reversed_pages_names['posts:profile']
        self.assertRedirects(response, redirect)

    def test_edit_post_form(self):
        """Валидная форма редактирует пост."""
        form_data = {
            'text': 'Тестовый текст 2'
        }

        response = self.authorized_client.post(
            PostFormTests.reversed_pages_names['posts:post_edit'],
            data=form_data,
            follow=True
        )

        edit_post = Post.objects.get(id=PostFormTests.post.id)
        self.assertEqual(edit_post.text, form_data["text"])

        redirect = PostFormTests.reversed_pages_names['posts:post_detail']
        self.assertRedirects(response, redirect)

    def test_edit_post_with_group_form(self):
        """Валидная форма редактирует пост."""
        form_data = {
            'text': 'Тестовый текст 2 c группой',
            'group': PostFormTests.group.pk
        }

        response = self.authorized_client.post(
            PostFormTests.reversed_pages_names['posts:post_edit'],
            data=form_data,
            follow=True
        )

        edit_post = Post.objects.get(id=PostFormTests.post.id)
        expected_values = {
            edit_post.text: form_data['text'],
            edit_post.group.pk: form_data['group']
        }

        for value, expected in expected_values.items():
            with self.subTest(value=value):
                self.assertEqual(value, expected)

        redirect = PostFormTests.reversed_pages_names['posts:post_detail']
        self.assertRedirects(response, redirect)

    def test_new_post_with_group_is_shown(self):
        posts_counts = dict()
        reversed_names = (
            PostFormTests.reversed_pages_names['posts:index'],
            PostFormTests.reversed_pages_names['posts:group_posts'],
            PostFormTests.reversed_pages_names['posts:profile']
        )
        for reversed_name in reversed_names:
            response = self.authorized_client.get(reversed_name)
            posts_count = len(response.context['page_obj'])
            posts_counts.update({reversed_name: posts_count})

        form_data = {
            'text': 'Тестовый текст поста с группой',
            'group': PostFormTests.group.pk,
            'author': PostFormTests.user
        }

        response = self.authorized_client.post(
            PostFormTests.reversed_pages_names['posts:post_create'],
            data=form_data,
            follow=True
        )

        for reversed_name in reversed_names:
            with self.subTest(reversed_name=reversed_name):
                response = self.authorized_client.get(reversed_name)
                posts_count = len(response.context['page_obj'])
                self.assertEqual(posts_count, posts_counts[reversed_name] + 1)
