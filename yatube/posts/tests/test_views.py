import shutil
import tempfile
from http import HTTPStatus
from typing import Dict, Any

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Post, Group, Follow, Comment
from ..utils import get_urls_info, get_reversed_names, OBJ_PER_PAGE

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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

        cls.user = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded
        )
        cls.follower_user = User.objects.create_user(username='follower')

        cls.urls_info = get_urls_info(
            cls.user.username,
            cls.group.slug,
            cls.post.id
        )
        cls.reversed_names = get_reversed_names(cls.urls_info)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsViewTests.user)
        self.follower = Client()
        self.follower.force_login(self.follower_user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""

        for url in PostsViewTests.urls_info:
            namespace = url['namespace']
            reverse_name = PostsViewTests.reversed_names[namespace]
            template = url['template']
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertTemplateUsed(response, template)

    def get_expected_context_for_post(self, post: Post) -> Dict[Any, Any]:
        """Возвращает поля поста и ожидаемые поля."""
        post_text_0 = post.text
        post_author_0 = post.author
        post_group_0 = post.group.title
        post_img_0 = post.image

        expected_context = {
            post_group_0: PostsViewTests.group.title,
            post_author_0: PostsViewTests.user,
            post_text_0: PostsViewTests.post.text,
            post_img_0: PostsViewTests.post.image
        }
        return expected_context

    def test_page_obj_show_right_context(self):
        """Страница постов отображает корректный контекст."""
        reversed_names = (
            PostsViewTests.reversed_names['posts:index'],
            PostsViewTests.reversed_names['posts:group_posts'],
            PostsViewTests.reversed_names['posts:profile']
        )

        for reversed_name in reversed_names:
            response = self.authorized_client.get(reversed_name)
            first_post = response.context['page_obj'][0]
            expected_content = self.get_expected_context_for_post(first_post)

            for value, expected in expected_content.items():
                with self.subTest(value=value):
                    self.assertEqual(value, expected)

    def test_group_list_and_profile_show_1_post(self):
        """Страницы группы и профиля отображают корректные посты."""
        reversed_names = (
            PostsViewTests.reversed_names['posts:group_posts'],
            PostsViewTests.reversed_names['posts:profile']
        )
        user = User.objects.create_user(username='NoName2')
        group = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug-2',
            description='Тестовое описание 2',
        )
        Post.objects.create(
            author=user,
            text='Тестовый текст 2',
            group=group
        )

        for reversed_name in reversed_names:
            with self.subTest(reversed_name=reversed_name):
                response = self.authorized_client.get(reversed_name)
                self.assertEqual(len(response.context['page_obj']), 1)

    def test_post_detail_show_correct_context(self):
        """Post detail отображает правильный контекстю"""
        reversed_name = PostsViewTests.reversed_names['posts:post_detail']
        response = self.authorized_client.get(reversed_name)

        post = response.context['post']
        self.assertEqual(post.id, 1)

    def test_post_create_show_correct_context(self):
        """Форма создания поста отображает правильный контекстю"""
        reversed_name = PostsViewTests.reversed_names['posts:post_create']

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }

        response = self.authorized_client.get(reversed_name)
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

        self.assertIsNone(response.context.get('is_edit', None))

    def test_post_edit_show_correct_context(self):
        """Форма редактирования поста отображает правильный контекстю"""
        reversed_url = PostsViewTests.reversed_names['posts:post_edit']

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }

        response = self.authorized_client.get(reversed_url)
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

        self.assertTrue(response.context['is_edit'])

    def test_added_comment_is_shown(self):
        """Комментарий создается и виден."""
        reversed_name = reverse(
            'posts:add_comment',
            kwargs={'post_id': PostsViewTests.post.id}
        )
        form_fields = {
            'text': 'Текст комментария',
        }
        comment_existing_before_creation = Comment.objects.filter(
            text='Текст комментария',
            post_id=PostsViewTests.post.id
        ).exists()
        self.assertFalse(comment_existing_before_creation)

        self.authorized_client.post(
            reversed_name,
            data=form_fields,
            follow=True)

        comment_existing_after_creation = Comment.objects.filter(
            text='Текст комментария',
            post_id=PostsViewTests.post.id
        ).exists()
        self.assertTrue(comment_existing_after_creation)

        post_detail = self.client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': PostsViewTests.post.id}
                    )
        )

        post_comment = post_detail.context['comments'][0]
        expected_values = {
            post_comment.author: PostsViewTests.user,
            post_comment.text: form_fields['text'],
        }
        for value, expected in expected_values.items():
            with self.subTest(value=value):
                self.assertEqual(value, expected)

    def test_auth_user_can_follow_and_unfollow(self):
        """Зарегестрированный пользователь может подписаться и отписаться."""
        reversed_follow = reverse(
            'posts:profile_follow',
            kwargs={'username': PostsViewTests.user.username}
        )
        reversed_unfollow = reverse(
            'posts:profile_unfollow',
            kwargs={'username': PostsViewTests.user.username}
        )

        self.follower.get(reversed_follow, follow=True)

        follow = Follow.objects.filter(
            user=PostsViewTests.follower_user,
            author=PostsViewTests.user
        ).exists()
        self.assertTrue(follow)

        self.follower.get(reversed_unfollow, follow=True)

        follow = Follow.objects.filter(
            user=PostsViewTests.follower_user,
            author=PostsViewTests.user
        ).exists()
        self.assertFalse(follow)

    def test_follow_author_is_shown_correctly(self):
        """Подписки корректно отображаются в Index Follow."""
        cache.clear()
        reversed_name = reverse(
            'posts:profile_follow',
            kwargs={'username': PostsViewTests.user.username}
        )
        self.follower.get(reversed_name, follow=True)

        response = self.follower.get(reverse('posts:follow_index'))
        post = response.context['page_obj'][0]
        expected_content = self.get_expected_context_for_post(post)

        for value, expected in expected_content.items():
            with self.subTest(value=value):
                self.assertEqual(
                    value,
                    expected,
                    msg='Пост автора из подписок отображается некорректно'
                )

        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertFalse(
            response.context['page_obj'],
            msg='Пост отображается у неподписанных пользователей'
        )

    def test_cache_index_page(self):
        """Страница Index сохраняет кэш."""

        reversed_name = reverse('posts:index')

        response = self.authorized_client.get(reversed_name)
        cached_context = response.content
        post = Post.objects.all().order_by('-id')[0]
        post.delete()
        response = self.authorized_client.get(reversed_name)
        self.assertEqual(response.content, cached_context)

        cache.clear()
        response = self.authorized_client.get(reversed_name)
        self.assertNotEqual(response.content, cached_context)


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug-',
            description='Тестовое описание',
        )
        cls.follower_user = User.objects.create_user(username='Follower')
        post_list = []
        cls.NUMBER_OF_POSTS = 13

        for i in range(cls.NUMBER_OF_POSTS):
            post_list.append(Post.objects.create(
                author=cls.user,
                text='Тестовый текст поста №' + str(i),
                group=cls.group
            ))
        Follow.objects.get_or_create(user=cls.follower_user, author=cls.user)

        cls.reversed_names = {
            reverse('posts:index'): len(Post.objects.all()),
            reverse(
                'posts:group_posts',
                kwargs={'slug': cls.group.slug}
            ): len(cls.group.posts.all()),
            reverse(
                'posts:profile',
                kwargs={'username': cls.user.username}
            ): len(cls.user.posts.all()),
            reverse(
                'posts:follow_index'
            ): len(
                Post.objects.filter(author__following__user=cls.follower_user)
            )
        }

    def setUp(self):
        self.client = Client()
        self.follower = Client()
        self.follower.force_login(PaginatorViewTest.follower_user)

    def test_first_page_contains_right_amount_of_posts(self):
        """Первая страница паджинатора работает корректно."""
        for reverse_name in PaginatorViewTest.reversed_names.keys():
            with self.subTest(reverse_name=reverse_name):
                response = self.follower.get(reverse_name)
                number_of_posts = len(response.context['page_obj'])
                self.assertEqual(number_of_posts, OBJ_PER_PAGE)

    def test_second_page_contains_right_amount_of_posts(self):
        """Вторая страница паджинатора работает корректно."""
        for url_name, posts_count in PaginatorViewTest.reversed_names.items():
            with self.subTest(reverse_name=url_name):
                response = self.follower.get(url_name, {'page': 2})
                obj_left = posts_count - OBJ_PER_PAGE
                if obj_left > OBJ_PER_PAGE:
                    self.assertEqual(
                        len(response.context['page_obj']),
                        OBJ_PER_PAGE)
                else:
                    self.assertEqual(
                        len(response.context['page_obj']),
                        obj_left % (OBJ_PER_PAGE + 1)
                    )
