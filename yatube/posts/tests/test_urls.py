from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from http import HTTPStatus
from posts.models import Post, Group
User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create(username="Test_User",)

        cls.group = Group.objects.create(
            title="группа",
            slug="one_group",
            description="проверка описания",
        )

        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )

        cls.post_url = f'/posts/{cls.post.id}/'
        cls.post_edit_url = f'/posts/{cls.post.id}/edit/'
        cls.public_urls = (
            ('/', 'index.html'),
            (f'/group/{cls.group.slug}/', 'group.html'),
            (f'/profile/{cls.user.username}/', 'profile.html'),
            (cls.post_url, 'post.html'),
        )
        cls.private_urls = (
            ('/create/', 'create_post.html'),
            (cls.post_edit_url, 'create_post.html')
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    # Проверяем общедоступные страницы
    def test_public_pages(self):
        for url, template in self.public_urls:
            response = self.guest_client.get(url)
            self.assertEqual(response.status_code, 200, template)

    # Проверяем доступ для авторизованного пользователя и автора
    def test_private_pages(self):
        for data in self.private_urls:
            response = self.authorized_client.get(data[0])
            self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверяем статус 404 для авторизованного пользователя
    def test_task_list_url_redirect_anonymous(self):
        """Страница /unexisting_page/ не существует."""
        response = self.authorized_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Проверка вызываемых шаблонов для каждого адреса
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/one_group/': 'posts/group_list.html',
            '/profile/Test_User/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/posts/1/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
