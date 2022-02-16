from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Post, Group

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
        )
        cls.public_urls_names = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.user.username}/': 'posts/profile.html',
            f'/posts/{cls.post.id}/': 'posts/post_detail.html'
        }
        cls.private_urls_names = {
            '/create/': 'posts/create_post.html',
            f'/posts/{cls.post.id}/edit/': 'posts/create_post.html'
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsURLTests.user)
        cache.clear()

    def test_public_urls_work(self):
        """Публичные URL доступны."""
        for address in PostsURLTests.public_urls_names.keys():
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unauth_user_cannot_access_private_urls(self):
        login_url = reverse('users:login')
        for address in PostsURLTests.private_urls_names.keys():
            with self.subTest(address=address):
                target_url = f'{login_url}?next={address}'
                response = self.client.get(address, follow=True)
                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertRedirects(response, target_url)

    def test_auth_user_can_access_private_urls(self):
        for address in PostsURLTests.private_urls_names.keys():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def only_author_can_edit_post(self):
        user_1 = User.objects.create_user(username='Not the author')
        not_the_author_of_post = Client()
        not_the_author_of_post.force_login(user_1)

        post_edit_url = f'/posts/{PostsURLTests.post.id}/'
        target_url = f'/posts/{PostsURLTests.post.id}/'

        response = self.not_the_author_of_post.get(post_edit_url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, target_url)

    def test_urls_uses_correct_template(self):
        public_urls = PostsURLTests.public_urls_names
        private_urls = PostsURLTests.private_urls_names
        all_urls = {**public_urls, **private_urls}
        for address, template in all_urls.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_unexisting_page(self):
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_only_authorized_user_can_comment(self):
        login_url = reverse('users:login')
        reversed_name = reverse(
            'posts:add_comment',
            kwargs={'post_id': PostsURLTests.post.id}
        )
        form_fields = {
            'text': 'Текст комментария',
        }

        target_url = f'{login_url}?next={reversed_name}%3Fform%3Dtext'
        response = self.client.get(
            reversed_name,
            {'form': form_fields},
            follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, target_url)
