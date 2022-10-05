import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from posts.models import Group, Post, Comment
from posts.forms import PostForm
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


# Для сохранения media-файлов в тестах будет использоваться
# временная папка TEMP_MEDIA_ROOT, а потом мы ее удалим
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Test_User')
        cls.group = Group.objects.create(title='группа0', slug='test_slug0',
                                         description='проверка описания0')

        cls.post = Post.objects.create(
            text='Тестовый заголовок',
            author=cls.author,
        )
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)
        cls.form = PostForm()

    def test_create_post(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(Post.objects.filter(text='Тестовый текст').exists())

    def test_edit_post(self):
        old_post = self.post
        form_data = {
            'text': 'Новый тестовый текст',
        }
        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        new_post = Post.objects.get(id=self.post.id)
        self.assertNotEqual(old_post.text, new_post.text)

    def test_unauth_user_cant_publish_post(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
        }
        self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        response = self.guest_client.get('/create/')
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_comment_guest_user_not_added(self):
        comments_count = Comment.objects.count()
        comment_form = {
            'text': 'Текст'
        }
        self.client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=comment_form,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)

    def test_comment_authorized_added(self):
        comments_count = Comment.objects.count()
        comment_form = {
            'text': 'Текст'
        }
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=comment_form,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
