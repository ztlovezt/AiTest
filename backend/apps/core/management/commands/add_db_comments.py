# -*- coding: utf-8 -*-
"""
为数据库表和字段添加中文注释的管理命令
用法: python manage.py add_db_comments
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps


class Command(BaseCommand):
    help = '为数据库表和字段添加中文注释'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='只显示将要执行的SQL，不实际执行',
        )
        parser.add_argument(
            '--app',
            type=str,
            dest='app_label',
            default=None,
            help='指定应用名称，只为该应用的模型添加注释',
        )
        parser.add_argument(
            '--tables-only',
            action='store_true',
            dest='tables_only',
            default=False,
            help='只为表添加注释，跳过字段注释',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        app_label = options['app_label']
        tables_only = options['tables_only']

        # 应用第三方库和Django内置模型中文补丁
        from apps.core.patches import patch_third_party_models, patch_django_builtin_models
        patch_third_party_models()
        patch_django_builtin_models()

        if dry_run:
            self.stdout.write(self.style.WARNING('=== 试运行模式 - 不实际执行SQL ===\n'))

        table_count = 0
        field_count = 0
        errors = []

        if app_label:
            try:
                app_configs = [apps.get_app_config(app_label)]
            except LookupError:
                self.stderr.write(self.style.ERROR(f'应用 {app_label} 不存在'))
                return
        else:
            app_configs = apps.get_app_configs()

        with connection.cursor() as cursor:
            for app_config in app_configs:
                for model in app_config.get_models():
                    table_name = model._meta.db_table
                    table_comment = str(model._meta.verbose_name)

                    table_sql = f"ALTER TABLE `{table_name}` COMMENT = '{self._escape_sql(table_comment)}';"

                    if dry_run:
                        self.stdout.write(f'[表] {table_sql}')
                    else:
                        try:
                            cursor.execute(table_sql)
                            table_count += 1
                            self.stdout.write(self.style.SUCCESS(f'[表] {table_name}: {table_comment}'))
                        except Exception as e:
                            errors.append(f'{table_name}: {e}')
                            self.stderr.write(self.style.ERROR(f'[表] {table_name}: {e}'))

                    if tables_only:
                        continue

                    for field in model._meta.fields:
                        field_name = field.column
                        field_comment = str(field.verbose_name)

                        if hasattr(field, 'help_text') and field.help_text:
                            field_comment = f"{field_comment} - {field.help_text}"

                        column_def = self._get_column_definition(cursor, table_name, field_name)
                        if not column_def:
                            continue

                        field_sql = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{field_name}` {column_def} COMMENT '{self._escape_sql(field_comment)}';"

                        if dry_run:
                            self.stdout.write(f'  [字段] {field_name}: {field_comment}')
                            self.stdout.write(f'         {field_sql}')
                        else:
                            try:
                                cursor.execute(field_sql)
                                field_count += 1
                            except Exception as e:
                                error_msg = str(e)
                                if 'DEFAULT_GENERATED' in error_msg or 'JSON' in column_def.upper():
                                    result = self._add_comment_for_json_field(
                                        cursor, table_name, field_name, field_comment, column_def
                                    )
                                    if result:
                                        field_count += 1
                                        self.stdout.write(self.style.SUCCESS(f'  [字段-JSON] {table_name}.{field_name}: {field_comment}'))
                                    else:
                                        errors.append(f'{table_name}.{field_name}: {e}')
                                        self.stderr.write(self.style.WARNING(f'  [字段] {table_name}.{field_name}: {e}'))
                                else:
                                    errors.append(f'{table_name}.{field_name}: {e}')
                                    self.stderr.write(self.style.WARNING(f'  [字段] {table_name}.{field_name}: {e}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'完成！表注释: {table_count}, 字段注释: {field_count}'))
        if errors:
            self.stdout.write(self.style.WARNING(f'错误数: {len(errors)}'))
            for error in errors:
                self.stdout.write(f'  - {error}')

    def _escape_sql(self, text):
        """转义SQL字符串中的特殊字符"""
        if text is None:
            return ''
        return str(text).replace("'", "''").replace('\\', '\\\\')

    def _get_column_definition(self, cursor, table_name, column_name):
        """从数据库获取字段的完整定义"""
        try:
            cursor.execute("""
                SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = %s 
                AND COLUMN_NAME = %s
            """, [table_name, column_name])
            result = cursor.fetchone()
            if not result:
                return None

            column_type, is_nullable, column_default, extra = result

            definition = column_type
            if is_nullable == 'NO':
                definition += ' NOT NULL'
            else:
                definition += ' NULL'

            if column_default is not None:
                if column_default == 'NULL':
                    pass
                elif column_default in ('CURRENT_TIMESTAMP',):
                    definition += f' DEFAULT {column_default}'
                else:
                    definition += f" DEFAULT '{column_default}'"

            if extra:
                definition += f' {extra}'

            return definition
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'获取字段定义失败 {table_name}.{column_name}: {e}'))
            return None

    def _add_comment_for_json_field(self, cursor, table_name, column_name, comment, column_def):
        """为JSON字段添加注释（处理DEFAULT_GENERATED问题）"""
        try:
            cursor.execute("""
                SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA, CHARACTER_SET_NAME, COLLATION_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = %s 
                AND COLUMN_NAME = %s
            """, [table_name, column_name])
            result = cursor.fetchone()
            if not result:
                return False

            column_type, is_nullable, column_default, extra, charset, collation = result

            definition = column_type
            if is_nullable == 'NO':
                definition += ' NOT NULL'
            else:
                definition += ' NULL'

            if extra and 'DEFAULT_GENERATED' in extra:
                extra = extra.replace('DEFAULT_GENERATED', '').strip()
                extra = ' '.join(extra.split())

            if extra:
                definition += f' {extra}'

            field_sql = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{column_name}` {definition} COMMENT '{self._escape_sql(comment)}';"
            cursor.execute(field_sql)
            return True
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'JSON字段注释失败 {table_name}.{column_name}: {e}'))
            return False
