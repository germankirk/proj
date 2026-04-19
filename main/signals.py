from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserKeys
from .crypto.crypto_utils import generate_user_keys


@receiver(post_save, sender=User)
def create_user_keys(sender, instance, created, **kwargs):
    """
    Автоматически генерирует ключи для нового пользователя
    """
    if created:
        # Генерируем ключи при создании пользователя
        public_key_pem = generate_user_keys(instance)
        # Сохраняем открытый ключ в БД
        UserKeys.objects.create(
            user=instance,
            public_key=public_key_pem
        )
