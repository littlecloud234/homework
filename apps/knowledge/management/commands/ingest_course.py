from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.models import Document


class Command(BaseCommand):
    help = "将课程文档提交解析入库（默认异步，--sync 可同步执行）"

    def add_arguments(self, parser):
        parser.add_argument("--course", help="课程代码，例如 CS101")
        parser.add_argument("--document", type=int, help="单个文档 ID")
        parser.add_argument("--sync", action="store_true", help="不使用 Celery，直接同步执行")
        parser.add_argument("--force", action="store_true", help="强制重新解析处理中的文档")

    def handle(self, *args, **options):
        from apps.knowledge.services.ingestion import ingest_document
        from apps.knowledge.tasks import ingest_document_task

        queryset = Document.objects.select_related("course")
        if options["document"]:
            queryset = queryset.filter(pk=options["document"])
        elif options["course"]:
            queryset = queryset.filter(course__code=options["course"])
        else:
            raise CommandError("请指定 --course 或 --document。")

        documents = list(queryset)
        if not documents:
            raise CommandError("没有找到符合条件的文档。")

        for document in documents:
            if options["sync"]:
                job = ingest_document(document.id, force=options["force"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{document.course.code}] {document.title} -> "
                        f"{job.status}, {job.chunk_count} 块"
                    )
                )
            else:
                result = ingest_document_task.delay(
                    document.id, force=options["force"]
                )
                self.stdout.write(
                    f"[{document.course.code}] {document.title} -> 已入队 {result.id}"
                )
