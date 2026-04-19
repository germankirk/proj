from django.db import models
from django.contrib.auth.models import User


class UserKeys(models.Model):
    """Хранение приватного и открытого ключа каждого пользователя"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='keys', verbose_name='Пользователь')
    public_key = models.TextField(verbose_name='Открытый ключ')
    # Приватный ключ НЕ хранится в БД, только в файловой системе!
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Ключи пользователя'
        verbose_name_plural = 'Ключи пользователей'
    
    def __str__(self):
        return f'Ключи пользователя {self.user.username}'


class SignedDocument(models.Model):
    """Информация о подписанных документах"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='signed_documents', verbose_name='Подписавший')
    original_filename = models.CharField(max_length=255, verbose_name='Оригинальное имя файла')
    file = models.FileField(upload_to='signed_docs/%Y/%m/%d/', verbose_name='Файл')
    signature = models.FileField(upload_to='signatures/%Y/%m/%d/', verbose_name='Подпись')
    file_hash = models.CharField(max_length=64, verbose_name='Хеш файла (SHA-256)')
    signed_at = models.DateTimeField(auto_now_add=True, verbose_name='Время подписания')
    is_verified = models.BooleanField(default=False, verbose_name='Проверена ли подпись')
    
    class Meta:
        ordering = ['-signed_at']
        verbose_name = 'Подписанный документ'
        verbose_name_plural = 'Подписанные документы'
    
    def __str__(self):
        return f'{self.original_filename} (подписано {self.user.username})'


class Task(models.Model):
    STATUS_CHOICES = [
        ('новая', 'Новая'),
        ('в_процессе', 'В процессе'),
        ('завершена', 'Завершена'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks', verbose_name='Автор')
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='новая', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'

    def __str__(self):
        return self.title


class Submission(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions', verbose_name='Задача', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions', verbose_name='Пользователь')
    file = models.FileField(upload_to='submissions/%Y/%m/%d/', verbose_name='Файл')
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата сдачи')

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Ответ на задачу'
        verbose_name_plural = 'Ответы на задачи'

    def __str__(self):
        return f'{self.user.username} - {self.task.title if self.task else "Общий файл"}'
