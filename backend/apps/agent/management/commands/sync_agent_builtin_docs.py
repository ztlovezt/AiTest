from django.core.management.base import BaseCommand

from apps.agent.services import sync_builtin_docs


class Command(BaseCommand):
    help = "同步 Agent 内置平台文档索引"

    def handle(self, *args, **options):
        result = sync_builtin_docs()
        self.stdout.write(
            self.style.SUCCESS(
                f"同步完成 created={result['created']} updated={result['updated']} chunks={result['chunks']}"
            )
        )
