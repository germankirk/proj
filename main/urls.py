from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('tasks/create/', views.create_task, name='create_task'),
    path('tasks/upload/', views.upload_file, name='upload_file'),
    path('tasks/', views.my_tasks, name='my_tasks'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/edit/', views.edit_task, name='edit_task'),
    path('tasks/<int:pk>/delete/', views.delete_task, name='delete_task'),
    path('tasks/<int:pk>/submit/', views.submit_task, name='submit_task'),
    path('tasks/<int:pk>/submissions/', views.task_submissions, name='task_submissions'),
    path('sign/', views.sign_file, name='sign_file'),
    path('verify/', views.verify_file, name='verify_file'),
    path('download/signature/<int:doc_id>/', views.download_signature, name='download_signature'),
    # Маршруты для проверки подписанных документов
    path('documents/<int:doc_id>/verify/', views.verify_signed_document, name='verify_signed_document'),
    path('users/<str:username>/public-key/', views.user_public_key, name='user_public_key'),
    path('my-public-key/', views.user_public_key, name='my_public_key'),
]
