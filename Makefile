PYTHON ?= python
MANAGE := $(PYTHON) manage.py
COURSE ?= CS101

# 本地默认使用 dev 配置；生产 Worker 请在部署环境中覆盖为 prod。
DJANGO_SETTINGS_MODULE ?= config.settings.dev
export DJANGO_SETTINGS_MODULE

.PHONY: help env install migrate makemigrations dev worker test check lint format \
	seed ingest superuser shell docker-up docker-down docker-logs docker-migrate vector-index clean

help:
	@echo "常用目标："
	@echo "  make env             复制 .env.example 为 .env"
	@echo "  make install         安装依赖"
	@echo "  make migrate         执行数据库迁移"
	@echo "  make dev             启动 Django 开发服务器"
	@echo "  make worker          启动 Celery Worker"
	@echo "  make seed            创建演示教师/学生/管理员/课程"
	@echo "  make ingest COURSE=CS101  同步解析课程文档"
	@echo "  make test            运行测试"
	@echo "  make check           Django 系统检查"
	@echo "  make lint            Ruff 静态检查"
	@echo "  make docker-up       Docker Compose 启动全套服务"
	@echo "  make docker-down     停止 Docker Compose"
	@echo "  make vector-index    创建 pgvector HNSW 索引"

env:
	@test -f .env || cp .env.example .env
	@echo ".env 已就绪，请填写模型密钥。"

install:
	$(PYTHON) -m pip install -r requirements.txt

makemigrations:
	$(MANAGE) makemigrations

migrate:
	$(MANAGE) migrate

dev:
	$(MANAGE) runserver 0.0.0.0:8000

worker:
	celery -A config worker -l info --concurrency=2

test:
	$(MANAGE) test

check:
	$(MANAGE) check

lint:
	ruff check .

format:
	ruff format .

seed:
	$(MANAGE) seed_demo

ingest:
	$(MANAGE) ingest_course --course $(COURSE) --sync

superuser:
	$(MANAGE) createsuperuser

shell:
	$(MANAGE) shell

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-migrate:
	docker compose exec web $(MANAGE) migrate

vector-index:
	docker compose exec -T db psql -U postgres -d teaching_agent < scripts/create_vector_index.sql

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache staticfiles
