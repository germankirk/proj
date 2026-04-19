from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main.models import UserKeys
from main.crypto.crypto_utils import generate_user_keys


class Command(BaseCommand):
    help = 'Generates RSA keys for existing users who do not have keys yet'

    def handle(self, *args, **options):
        users_without_keys = User.objects.filter(keys__isnull=True)
        
        if not users_without_keys.exists():
            self.stdout.write(self.style.SUCCESS('All users already have keys'))
            return
        
        self.stdout.write(f'Generating keys for {users_without_keys.count()} users...')
        
        for user in users_without_keys:
            try:
                public_key_pem = generate_user_keys(user)
                UserKeys.objects.create(
                    user=user,
                    public_key=public_key_pem
                )
                self.stdout.write(self.style.SUCCESS(f'✓ Generated keys for {user.username}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Failed to generate keys for {user.username}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('Key generation completed'))
