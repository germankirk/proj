from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Task, Submission


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input'})
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-input'})
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-input'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Этот email уже используется.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Это имя пользователя уже занято.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(
        label='Имя пользователя или Email',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-input'})
    )


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'status']
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'status': 'Статус'
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Введите название задачи'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Введите описание задачи', 'rows': 6}),
            'status': forms.Select(attrs={'class': 'form-input'}),
        }


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file', 'comment']
        labels = {
            'file': 'Файл',
            'comment': 'Комментарий (опционально)'
        }
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-input'}),
            'comment': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Добавьте комментарий к вашему ответу', 'rows': 4}),
        }


class SignFileForm(forms.Form):
    """Форма для подписания файлов"""
    file = forms.FileField(
        label='Выберите файл',
        widget=forms.FileInput(attrs={'class': 'form-input'})
    )

