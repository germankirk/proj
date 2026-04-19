import os
from django.conf import settings
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed


def generate_user_keys(user):
    """
    Генерирует RSA-2048 ключи для пользователя
    Приватный ключ сохраняется в файловую систему (защищена паролем пользователя)
    Открытый ключ возвращается для сохранения в БД
    
    Args:
        user: объект User из Django
    
    Returns:
        str: открытый ключ в формате PEM
    """
    # Создаём директорию для ключей, если её нет
    user_keys_dir = os.path.join(settings.KEYS_DIR, f'user_{user.id}')
    os.makedirs(user_keys_dir, exist_ok=True)
    
    # Генерируем RSA-2048 ключевую пару
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    public_key = private_key.public_key()
    
    # Сохраняем открытый ключ в БД (в виде PEM)
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    # Сохраняем приватный ключ в файловую систему в защищённом виде
    # (защита пароля пользователя - замещается на реальный пароль при необходимости)
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()  # TODO: добавить шифрование паролем
    )
    
    private_key_path = os.path.join(user_keys_dir, 'private_key.pem')
    with open(private_key_path, 'wb') as f:
        f.write(private_key_pem)
    
    # Устанавливаем права доступа только для владельца (Linux/Mac)
    try:
        os.chmod(private_key_path, 0o600)
    except:
        pass  # Windows может не поддерживать chmod
    
    return public_key_pem


def get_user_private_key(user, password: bytes = None):
    """
    Загружает приватный ключ пользователя
    
    Args:
        user: объект User из Django
        password: пароль для расшифровки ключа (если он зашифрован)
    
    Returns:
        Объект приватного ключа из cryptography
    """
    user_keys_dir = os.path.join(settings.KEYS_DIR, f'user_{user.id}')
    private_key_path = os.path.join(user_keys_dir, 'private_key.pem')
    
    if not os.path.exists(private_key_path):
        raise FileNotFoundError(f"Приватный ключ пользователя {user.username} не найден")
    
    with open(private_key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=password
        )
    
    return private_key


def sign_file_with_user_key(file_path, user, password: bytes = None):
    """
    Подписывает файл приватным ключом пользователя
    
    Args:
        file_path: путь к файлу
        user: объект User из Django
        password: пароль ключа (если необходимо)
    
    Returns:
        tuple: (signature, file_hash) - подпись и хеш файла
    """
    # читаем файл
    with open(file_path, "rb") as f:
        data = f.read()

    # считаем хеш
    digest = hashes.Hash(hashes.SHA256())
    digest.update(data)
    file_hash = digest.finalize()

    # загружаем приватный ключ пользователя
    private_key = get_user_private_key(user, password)

    # создаём подпись
    signature = private_key.sign(
        file_hash,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        Prehashed(hashes.SHA256())
    )

    return signature, file_hash.hex()


def verify_signature_with_user_key(file_path, signature, user):
    """
    Проверяет подпись файла, используя открытый ключ пользователя из БД
    
    Args:
        file_path: путь к файлу
        signature: подпись в формате bytes или hex
        user: объект User из Django
    
    Returns:
        bool: True если подпись верна, False если нет
    """
    try:
        # читаем файл
        with open(file_path, "rb") as f:
            data = f.read()

        # считаем хеш
        digest = hashes.Hash(hashes.SHA256())
        digest.update(data)
        file_hash = digest.finalize()

        # преобразуем подпись из hex в bytes если необходимо
        if isinstance(signature, str):
            signature = bytes.fromhex(signature)

        # загружаем открытый ключ пользователя из БД
        from main.models import UserKeys
        try:
            user_keys = UserKeys.objects.get(user=user)
            public_key_pem = user_keys.public_key.encode('utf-8')
        except UserKeys.DoesNotExist:
            return False

        public_key = serialization.load_pem_public_key(public_key_pem)

        # проверяем подпись
        public_key.verify(
            signature,
            file_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            Prehashed(hashes.SHA256())
        )

        return True

    except Exception as e:
        print(f"Ошибка при проверке подписи: {e}")
        return False


def sign_hash(file_path, password: bytes):
    """
    Подписывает файл приватным ключом (старая функция для совместимости)
    
    Args:
        file_path: путь к файлу
        password: пароль ключа в формате bytes
    
    Returns:
        signature: подпись в формате bytes
    """
    # читаем файл
    with open(file_path, "rb") as f:
        data = f.read()

    # считаем хеш
    digest = hashes.Hash(hashes.SHA256())
    digest.update(data)
    file_hash = digest.finalize()

    # загружаем приватный ключ
    private_key_path = os.path.join(settings.KEYS_DIR, "private_key.pem")

    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=password
        )

    # создаём подпись
    signature = private_key.sign(
        file_hash,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        Prehashed(hashes.SHA256())
    )

    return signature


def sign_file_with_central_key(file_path):
    """
    Подписывает файл центральным приватным ключом (без прямого шифрования)
    
    Args:
        file_path: путь к файлу
    
    Returns:
        tuple: (signature, file_hash) - подпись и хеш файла в hex
    """
    try:
        # читаем файл
        with open(file_path, "rb") as f:
            data = f.read()

        # считаем хеш
        digest = hashes.Hash(hashes.SHA256())
        digest.update(data)
        file_hash = digest.finalize()

        # загружаем центральный приватный ключ
        private_key_path = os.path.join(settings.KEYS_DIR, "private_key.pem")

        with open(private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None  # Центральный ключ не зашифрован
            )

        # создаём подпись
        signature = private_key.sign(
            file_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            Prehashed(hashes.SHA256())
        )

        return signature, file_hash.hex()
    
    except Exception as e:
        print(f"Ошибка при подписи файла: {e}")
        raise


def verify_signature(file_path, signature_path, password: bytes = None):
    """
    Проверяет подпись файла (старая функция для совместимости)
    
    Args:
        file_path: путь к файлу
        signature_path: путь к файлу подписи
        password: пароль ключа (не требуется для открытого ключа)
    
    Returns:
        bool: True если подпись верна, False если нет
    """
    try:
        # читаем файл
        with open(file_path, "rb") as f:
            data = f.read()

        # считаем хеш
        digest = hashes.Hash(hashes.SHA256())
        digest.update(data)
        file_hash = digest.finalize()

        # загружаем подпись
        with open(signature_path, "rb") as f:
            signature = f.read()

        # загружаем открытый ключ
        public_key_path = os.path.join(settings.KEYS_DIR, "public_key.pem")

        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())

        # проверяем подпись
        public_key.verify(
            signature,
            file_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            Prehashed(hashes.SHA256())
        )

        return True

    except Exception as e:
        print(f"Ошибка при проверке подписи: {e}")
        return False
