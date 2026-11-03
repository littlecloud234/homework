"""Celery 配置：文档解析与向量化等耗时任务走异步队列。"""
import os

from celery import Celery

# 生产为默认值；本地管理命令/Worker 显式使用 config.settings.dev。
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("teaching_agent")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
