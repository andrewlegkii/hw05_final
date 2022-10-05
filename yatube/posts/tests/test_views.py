import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from posts.models import Post, Group, Follow
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

User = get_user_model()

# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


# Для сохранения media-файлов в тестах будет использоваться
# временная папка TEMP_MEDIA_ROOT, а потом мы ее удалим
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД
        cls.user = User.objects.create(username="Test_User",)

        cls.group = Group.objects.create(
            title="группа0",
            slug="test_slug0",
            description="проверка описания0",
        )

        small_gif = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
                     b'\x01\x00\x80\x00\x00\x00\x00\x00'
                     b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                     b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                     b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                     b'\x0A\x00\x3B'
                     )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        for i in range(13):
            cls.post = Post.objects.create(
                text='Тестовый текст0',
                author=cls.user,
                group=Group.objects.get(slug='test_slug0'),
                image=uploaded
            )

        post_args = 1
        cls.index_url = ('posts:index', 'posts/index.html', None)
        cls.group_url = ('posts:group_list', 'posts/group_list.html',
                         cls.group.slug)
        cls.profile_url = ('posts:profile', 'posts/profile.html',
                           cls.user.username)
        cls.post_url = ('posts:post_detail', 'posts/post_detail.html',
                        post_args)
        cls.new_post_url = ('posts:post_create', 'posts/create_post.html',
                            None)
        cls.edit_post_url = ('posts:post_edit', 'posts/create_post.html',
                             post_args)
        cls.paginated_urls = (
            cls.index_url,
            cls.group_url,
            cls.profile_url
        )
        cls.pages_names = [
            reverse(cls.index_url[0]),
            reverse(cls.group_url[0], kwargs={'slug': cls.group_url[2]}),
            reverse(cls.profile_url[0],
                    kwargs={'username': cls.profile_url[2]}),
        ]
        cls.templates_pages_names = {
            reverse(cls.index_url[0]): cls.index_url[1],
            reverse(cls.group_url[0], kwargs={'slug': cls.group_url[2]}):
            cls.group_url[1],
            reverse(cls.profile_url[0],
                    kwargs={'username': cls.profile_url[2]}):
            cls.profile_url[1],
            reverse(cls.post_url[0], kwargs={'post_id': cls.post_url[2]}):
            cls.post_url[1],
            reverse(cls.edit_post_url[0],
                    kwargs={'post_id': cls.edit_post_url[2]}):
            cls.edit_post_url[1],
            reverse(cls.new_post_url[0]): cls.new_post_url[1],
        }
        cls.reverse_page_names_post = {
            reverse(cls.index_url[0]): cls.group_url[2],
            reverse(cls.group_url[0], kwargs={'slug': cls.group_url[2]}):
            cls.group_url[2],
            reverse(cls.profile_url[0],
                    kwargs={'username': cls.profile_url[2]}):
            cls.group_url[2]
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный+авторизованый клиент и фолловера
        self.guest_client = Client()
        self.user = User.objects.get(username="Test_User")
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.follower = User.objects.create_user(username='Follower')
        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.follower)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Проверяем, что при обращении к name вызывается HTML-шаблон
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    # Проверка словаря контекста страниц
    def test_index_page_show_correct_context(self):
        """index,group_list,profile с правильным контекстом."""
        for template in self.pages_names:
            with self.subTest(template=template):
                response = self.guest_client.get(template)
                first_object = response.context['page_obj'][0]
                task_author_0 = first_object.author.username
                task_text_0 = first_object.text
                task_group_0 = first_object.group.title
                self.assertEqual(task_author_0, 'Test_User')
                self.assertEqual(task_text_0, 'Тестовый текст0')
                self.assertEqual(task_group_0, 'группа0')

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(self.post_url[0],
                                                      args=[self.post_url[2]]))
        post = response.context['post']
        self.assertEqual(post.pk, self.post_url[2])

    def test_create_post_edit_show_correct_context(self):
        """Шаблон create_post(edit) сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(self.edit_post_url[0],
                                              args=[self.edit_post_url[2]]))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_post_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(self.new_post_url[0]))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_urls_first_page_contains_10_records(self):
        """10 постов на страницу у index, group_page and profile"""
        for template in self.pages_names:
            with self.subTest(template=template):
                response = self.guest_client.get(template)
                self.assertEqual(len(response.context['page_obj']), 10)

    def test_urls_second_page_contains_3_records(self):
        """3 поста на второй странице index, group_page and profile"""
        for template in self.pages_names:
            with self.subTest(template=template):
                response = self.guest_client.get(template + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 3)

    def test_post_in_index_group_profile_after_create(self):
        """созданный пост появился на главной, в группе, в профиле."""
        for value, expected in self.reverse_page_names_post.items():
            response = self.authorized_client.get(value)
            for object in response.context['page_obj']:
                post_group = object.group.slug
                with self.subTest(value=value):
                    self.assertEqual(post_group, expected)

    def test_post_not_in_foreign_group(self):
        """Созданного поста НЕТ в чужой группе"""
        Group.objects.create(
            title='группа777',
            slug='test_slug777',
            description='проверка описания777',
        )
        response = self.authorized_client.get(
            reverse(self.group_url[0], kwargs={'slug': 'test_slug777'})
        )
        for object in response.context['page_obj']:
            post_slug = object.group.slug
            self.assertNotEqual(post_slug, self.group.slug)

    def test_cache_index_page(self):
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        cached_response = response.content
        post = Post.objects.get(pk=1)
        post.delete()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, cached_response)

    def test_follow_author(self):
        before_follow_num = (Follow.objects.filter(author=self.user).count())
        self.authorized_follower.get(reverse('posts:profile_follow',
                                     kwargs={'username': self.user}))
        after_follow_num = Follow.objects.filter(author=self.user).count()
        self.assertNotEqual(before_follow_num, after_follow_num)
        self.assertTrue(
            Follow.objects.filter(
                user=self.follower,
                author=self.user
            ).exists()
        )

    def test_unfollow_author(self):
        self.authorized_follower.get(reverse('posts:profile_follow',
                                     kwargs={'username': self.user}))
        after_follow_num = Follow.objects.filter(author=self.user).count()
        self.authorized_follower.get(reverse('posts:profile_unfollow',
                                     kwargs={'username': self.user}))
        after_unfollow_num = Follow.objects.filter(author=self.user).count()
        self.assertNotEqual(after_follow_num, after_unfollow_num)

    def test_not_follower_cant_see_post(self):
        not_follower = User.objects.create_user(username='Not_Follower')
        authorized_not_follower = Client()
        authorized_not_follower.force_login(not_follower)

        follow_post = Post.objects.create(text='Текст', author=self.user,)
        not_follower_response = (
            authorized_not_follower.get(reverse('posts:follow_index'))
        )
        self.assertNotIn(
            follow_post,
            not_follower_response.context.get('page_obj')
        )
