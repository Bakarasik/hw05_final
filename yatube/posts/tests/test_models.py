from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст поста больше 15-ти символов',
        )

    def test_model_have_correct_object_names(self):
        """Модели Post и Group имею корректрый метод str"""
        group = PostModelTest.group
        post = PostModelTest.post
        str_method = {
            group: group.title,
            post: post.text[:15]
        }
        for field, expected_value in str_method.items():
            with self.subTest(field=type(field).__name__):
                self.assertEqual(str(field), expected_value)
