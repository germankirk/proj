from django.contrib import admin
from .models import Task, Submission


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description', 'author__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Информация', {
            'fields': ('title', 'description', 'status')
        }),
        ('Автор', {
            'fields': ('author',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'submitted_at')
    list_filter = ('submitted_at', 'task')
    search_fields = ('user__username', 'task__title')
    readonly_fields = ('submitted_at',)
    fieldsets = (
        ('Задача и ответ', {
            'fields': ('task', 'user', 'file', 'comment')
        }),
        ('Дата', {
            'fields': ('submitted_at',),
            'classes': ('collapse',)
        }),
    )
