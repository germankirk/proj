from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpResponse, FileResponse
from datetime import timedelta
import os
import hashlib
from .forms import RegisterForm, LoginForm, TaskForm, SubmissionForm, SignFileForm
from .models import Task, Submission, UserKeys, SignedDocument
from .crypto.crypto_utils import sign_hash, verify_signature, sign_file_with_user_key, verify_signature_with_user_key, calculate_file_hash


def index(request):
    return render(request, 'index.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('main:index')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна! Вы вошли в аккаунт.')
            return redirect('main:index')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = RegisterForm()
    
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('main:index')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Проверяем по username или email
            user = None
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.username}!')
                return redirect('main:index')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из аккаунта.')
    return redirect('main:index')


@login_required(login_url='main:login')
def create_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.author = request.user
            task.save()
            messages.success(request, 'Задача успешно создана!')
            return redirect('main:my_tasks')
    else:
        form = TaskForm()
    
    return render(request, 'create_task.html', {'form': form})


@login_required(login_url='main:login')
def my_tasks(request):
    tasks = Task.objects.filter(author=request.user)
    return render(request, 'my_tasks.html', {'tasks': tasks})


@login_required(login_url='main:login')
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    if task.author != request.user:
        messages.error(request, 'У вас нет доступа к этой задаче.')
        return redirect('main:my_tasks')
    
    return render(request, 'task_detail.html', {'task': task})


@login_required(login_url='main:login')
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    if task.author != request.user:
        messages.error(request, 'У вас нет доступа к этой задаче.')
        return redirect('main:my_tasks')
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Задача успешно обновлена!')
            return redirect('main:task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task)
    
    return render(request, 'edit_task.html', {'form': form, 'task': task})


@login_required(login_url='main:login')
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    if task.author != request.user:
        messages.error(request, 'У вас нет доступа к этой задаче.')
        return redirect('main:my_tasks')
    
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Задача успешно удалена!')
        return redirect('main:my_tasks')
    
    return render(request, 'delete_task.html', {'task': task})


@login_required(login_url='main:login')
def submit_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    # Проверяем, что это не автор задачи
    if task.author == request.user:
        messages.error(request, 'Вы не можете сдавать свою собственную задачу.')
        return redirect('main:task_detail', pk=task.pk)
    
    # Проверяем, есть ли уже ответ от этого пользователя
    existing_submission = Submission.objects.filter(task=task, user=request.user).first()
    
    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Создаём новый ответ или обновляем существующий
                if existing_submission:
                    submission = form.save(commit=False)
                    submission.id = existing_submission.id
                    submission.task = task
                    submission.user = request.user
                else:
                    submission = form.save(commit=False)
                    submission.task = task
                    submission.user = request.user
                
                submission.save()
                
                # Автоматически подписываем файл
                file_path = submission.file.path
                try:
                    signature, file_hash = sign_file_with_user_key(file_path, request.user)
                    
                    # Сохраняем подписанный документ
                    signed_doc = SignedDocument(
                        user=request.user,
                        original_filename=submission.file.name,
                        file=submission.file,
                        file_hash=file_hash,
                        is_verified=True
                    )
                    
                    # Сохраняем подпись в файл
                    sig_filename = f'{submission.file.name}.sig'
                    sig_path = os.path.join(settings.MEDIA_ROOT, 'signatures', request.user.username, sig_filename)
                    os.makedirs(os.path.dirname(sig_path), exist_ok=True)
                    
                    with open(sig_path, 'wb') as f:
                        f.write(signature)
                    
                    # Сохраняем путь к подписи в модель
                    signed_doc.signature.name = f'signatures/{request.user.username}/{sig_filename}'
                    signed_doc.save()
                    
                    if existing_submission:
                        messages.success(request, 'Ваш ответ успешно обновлён и подписан!')
                    else:
                        messages.success(request, 'Задача успешно сдана и подписана!')
                    
                except Exception as e:
                    # Если подписание не удалось, сохраняем файл без подписи
                    messages.warning(request, f'Файл загружен, но подписание не удалось: {str(e)}')
                
                return redirect('main:task_detail', pk=task.pk)
            
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении: {str(e)}')
    else:
        if existing_submission:
            form = SubmissionForm(instance=existing_submission)
        else:
            form = SubmissionForm()
    
    return render(request, 'submit_task.html', {
        'form': form,
        'task': task,
        'existing_submission': existing_submission
    })


@login_required(login_url='main:login')
def task_submissions(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    # Только автор может видеть ответы
    if task.author != request.user:
        messages.error(request, 'У вас нет доступа к ответам этой задачи.')
        return redirect('main:my_tasks')
    
    submissions = task.submissions.all()
    
    return render(request, 'task_submissions.html', {
        'task': task,
        'submissions': submissions
    })


@login_required(login_url='main:login')
def upload_file(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        comment = request.POST.get('comment', '')
        
        if file:
            # Создаём новый файл в медиа папке
            submission = Submission()
            submission.user = request.user
            submission.file = file
            submission.comment = comment
            submission.save()
            
            messages.success(request, 'Файл успешно загружен!')
        else:
            messages.error(request, 'Пожалуйста, выберите файл.')
    
    return redirect('main:my_tasks')


@login_required(login_url='main:login')

@login_required(login_url='main:login')
def sign_file(request):
    """Подпись файла приватным ключом пользователя"""
    if request.method == 'POST':
        form = SignFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file = request.FILES['file']
                
                # Сохраняем файл во временной папке
                upload_path = os.path.join(settings.MEDIA_ROOT, 'uploads', file.name)
                
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                
                file_content = b''
                with open(upload_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
                        file_content += chunk
                
                # Подписываем файл приватным ключом пользователя
                signature, file_hash = sign_file_with_user_key(upload_path, request.user)
                
                # Сохраняем подпись в файловую систему
                sig_path = os.path.join(settings.MEDIA_ROOT, 'signatures', file.name + '.sig')
                os.makedirs(os.path.dirname(sig_path), exist_ok=True)
                
                with open(sig_path, 'wb') as f:
                    f.write(signature)
                
                # Сохраняем содержимое файла рядом с подписью
                content_path = os.path.join(settings.MEDIA_ROOT, 'signatures', file.name + '.txt')
                with open(content_path, 'wb') as f:
                    f.write(file_content)
                
                # Сохраняем информацию о подписании в БД
                try:
                    from django.core.files.base import ContentFile
                    
                    signed_doc = SignedDocument(
                        user=request.user,
                        original_filename=file.name,
                        file_hash=file_hash,
                        is_verified=True
                    )
                    
                    # Сохраняем основной файл в БД
                    signed_doc.file.save(file.name, ContentFile(file_content))
                    
                    # Сохраняем подпись в БД
                    signed_doc.signature.save(file.name + '.sig', ContentFile(signature))
                    
                    signed_doc.save()
                except Exception as e:
                    print(f"Ошибка при сохранении в БД: {e}")
                    # Не прерываем процесс, если сохранение в БД не удалось
                
                messages.success(request, f'Файл {file.name} успешно подписан! Подпись сохранена.')
                
                # Возвращаем правильный путь для скачивания из БД
                try:
                    signed_doc = SignedDocument.objects.filter(
                        user=request.user,
                        original_filename=file.name
                    ).latest('signed_at')
                    signature_path = f'/download/signature/{signed_doc.id}/'
                except:
                    signature_path = f'/media/signatures/{file.name}.sig'
                
                return render(request, 'sign_file.html', {
                    'form': form,
                    'signed': True,
                    'filename': file.name,
                    'signature_path': signature_path
                })
                
            except FileNotFoundError as e:
                print(f"FileNotFoundError в sign_file: {str(e)}")
                messages.error(request, f'Ошибка: {str(e)}')
            except Exception as e:
                print(f"Exception в sign_file: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Ошибка при подписании: {str(e)}')
    else:
        form = SignFileForm()
    
    return render(request, 'sign_file.html', {'form': form})


@login_required(login_url='main:login')
def download_signature(request, doc_id):
    """Безопасное скачивание подписи из БД"""
    try:
        signed_doc = SignedDocument.objects.get(id=doc_id)
        
        # Проверяем что пользователь может скачать эту подпись
        # (свою или если он администратор)
        if signed_doc.user != request.user and not request.user.is_staff:
            messages.error(request, 'У вас нет прав на скачивание этой подписи.')
            return redirect('main:index')
        
        # Открываем и отправляем файл подписи
        if signed_doc.signature:
            response = FileResponse(signed_doc.signature.open('rb'))
            response['Content-Disposition'] = f'attachment; filename="{signed_doc.original_filename}.sig"'
            return response
        else:
            messages.error(request, 'Подпись не найдена.')
            return redirect('main:index')
            
    except SignedDocument.DoesNotExist:
        messages.error(request, 'Подписанный документ не найден.')
        return redirect('main:index')
    except Exception as e:
        print(f"Ошибка при скачивании подписи: {e}")
        messages.error(request, f'Ошибка при скачивании: {str(e)}')
        return redirect('main:index')


@login_required(login_url='main:login')
def verify_file(request):
    """Проверка подписи файла"""
    if request.method == 'POST':
        file = request.FILES.get('file')
        signature_file = request.FILES.get('signature')
        
        if file and signature_file:
            try:
                # Сохраняем оба файла временно
                file_path = os.path.join(settings.MEDIA_ROOT, 'uploads', file.name)
                sig_path = os.path.join(settings.MEDIA_ROOT, 'signatures', signature_file.name)
                
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                os.makedirs(os.path.dirname(sig_path), exist_ok=True)
                
                with open(file_path, 'wb+') as dest:
                    for chunk in file.chunks():
                        dest.write(chunk)
                
                with open(sig_path, 'wb+') as dest:
                    for chunk in signature_file.chunks():
                        dest.write(chunk)
                
                # Рассчитываем хеш файла для поиска в БД
                file_hash = calculate_file_hash(file_path)
                
                # Ищем информацию о подписании в БД
                signer = None
                signed_at = None
                is_valid = False
                
                try:
                    signed_doc = SignedDocument.objects.get(file_hash=file_hash)
                    signer = signed_doc.user
                    signed_at = signed_doc.signed_at + timedelta(hours=3)
                    
                    # Если документ найден в БД - проверяем подпись с пользовательским ключом
                    # Прочитаем содержимое файла подписи
                    with open(sig_path, 'rb') as f:
                        signature_bytes = f.read()
                    
                    is_valid = verify_signature_with_user_key(file_path, signature_bytes, signer)
                except SignedDocument.DoesNotExist:
                    # Если документ не найден в БД - пытаемся проверить с центральным ключом
                    is_valid = verify_signature(file_path, sig_path)
                except Exception as e:
                    print(f"Ошибка при проверке через БД: {e}")
                    is_valid = False
                
                # Загружаем содержимое файла если подпись верна
                file_content = ''
                if is_valid:
                    # Пытаемся загрузить содержимое из .txt файла рядом с подписью
                    content_path = sig_path.replace('.sig', '.txt')
                    if os.path.exists(content_path):
                        try:
                            with open(content_path, 'r', encoding='utf-8', errors='replace') as f:
                                file_content = f.read()
                        except:
                            pass
                
                return render(request, 'verify_file.html', {
                    'verified': True,
                    'is_valid': is_valid,
                    'filename': file.name,
                    'file_content': file_content,
                    'message': '✓ Подпись верна!' if is_valid else '✗ Подпись не совпадает!',
                    'signer': signer,
                    'signed_at': signed_at,
                    'file_hash': file_hash,
                })
                
            except Exception as e:
                messages.error(request, f'Ошибка при проверке: {str(e)}')
    
    return render(request, 'verify_file.html', {})


@login_required(login_url='main:login')
def user_public_key(request, username=None):
    """Просмотр открытого ключа пользователя"""
    
    if username:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, 'Пользователь не найден.')
            return redirect('main:index')
    else:
        user = request.user
    
    try:
        user_keys = UserKeys.objects.get(user=user)
        
        return render(request, 'user_public_key.html', {
            'user_profile': user,
            'public_key': user_keys.public_key,
            'created_at': user_keys.created_at
        })
    except UserKeys.DoesNotExist:
        messages.error(request, f'Ключи пользователя {user.username} не найдены.')
        return redirect('main:index')


def verify_signed_document(request, doc_id):
    """Публичная проверка подписанного документа (без логина)"""
    try:
        signed_doc = SignedDocument.objects.get(id=doc_id)
        
        # Проверяем подпись
        file_path = signed_doc.file.path
        sig_path = signed_doc.signature.path
        
        try:
            is_valid = verify_signature_with_user_key(file_path, signed_doc.file_hash, signed_doc.user)
        except:
            is_valid = False
        
        return render(request, 'verify_signed_document.html', {
            'signed_doc': signed_doc,
            'is_valid': is_valid,
            'signer': signed_doc.user,
            'signed_at': signed_doc.signed_at + timedelta(hours=3),
            'original_filename': signed_doc.original_filename
        })
    except SignedDocument.DoesNotExist:
        messages.error(request, 'Документ не найден.')
        return redirect('main:index')

