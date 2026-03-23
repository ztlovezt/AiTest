import os
import traceback
from django.utils import timezone
from django.db import transaction
import openpyxl

from apps.testcases.models import TestCase, TestCaseImportRecord

def process_test_case_import(record_id):
    try:
        record = TestCaseImportRecord.objects.get(id=record_id)
    except TestCaseImportRecord.DoesNotExist:
        return
        
    record.status = 'running'
    record.started_at = timezone.now()
    record.save(update_fields=['status', 'started_at'])
    
    file_path = record.file.path if record.file else None
    if not file_path or not os.path.exists(file_path):
        record.status = 'failed'
        record.logs = '导入文件不存在'
        record.finished_at = timezone.now()
        record.save()
        return

    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet = wb.active
        
        # Check headers
        headers = [str(cell.value).strip() if cell.value else '' for cell in sheet[1]]
        
        expected_headers = {
            '用例标题': 'title',
            '用例描述': 'description',
            '前置条件': 'preconditions',
            '操作步骤': 'steps',
            '预期结果': 'expected_result',
            '优先级': 'priority',
            '状态': 'status',
            '测试类型': 'test_type'
        }
        
        col_map = {}
        for idx, h in enumerate(headers):
            if h in expected_headers:
                col_map[expected_headers[h]] = idx

        if 'title' not in col_map or 'expected_result' not in col_map:
            raise ValueError("模板错误：缺少必填列 '用例标题' 或 '预期结果'")

        total_rows = sheet.max_row - 1
        record.total_rows = total_rows
        record.save(update_fields=['total_rows'])

        success_count = 0
        failed_count = 0
        duplicate_count = 0
        error_summary = []

        priority_map = {'低': 'low', '中': 'medium', '高': 'high', '紧急': 'critical'}
        status_map = {'草稿': 'draft', '激活': 'active', '废弃': 'deprecated'}
        type_map = {
            '功能测试': 'functional', '集成测试': 'integration', 'API测试': 'api',
            'UI测试': 'ui', '性能测试': 'performance', '安全测试': 'security'
        }

        # Process rows
        for row_idx in range(2, sheet.max_row + 1):
            row_data = sheet[row_idx]
            
            # Extract data
            def get_val(key, default=''):
                if key in col_map:
                    val = row_data[col_map[key]].value
                    return str(val).strip() if val is not None else default
                return default

            title = get_val('title')
            if not title:
                failed_count += 1
                error_summary.append({'row': row_idx, 'error': '用例标题为空'})
                continue
                
            expected_result = get_val('expected_result')
            if not expected_result:
                failed_count += 1
                error_summary.append({'row': row_idx, 'error': '预期结果为空'})
                continue

            priority_text = get_val('priority', '中')
            status_text = get_val('status', '草稿')
            type_text = get_val('test_type', '功能测试')

            priority = priority_map.get(priority_text, 'medium')
            status = status_map.get(status_text, 'draft')
            test_type = type_map.get(type_text, 'functional')

            # Check duplicate (Optional: skip if exists in same project)
            if TestCase.objects.filter(project_id=record.project_id, title=title).exists():
                duplicate_count += 1
                failed_count += 1
                error_summary.append({'row': row_idx, 'error': f'项目中已存在同名用例: {title}'})
                continue

            try:
                TestCase.objects.create(
                    project_id=record.project_id,
                    title=title,
                    description=get_val('description'),
                    preconditions=get_val('preconditions'),
                    steps=get_val('steps'),
                    expected_result=expected_result,
                    priority=priority,
                    status=status,
                    test_type=test_type,
                    author=record.created_by
                )
                success_count += 1
            except Exception as e:
                failed_count += 1
                error_summary.append({'row': row_idx, 'error': f'保存失败: {str(e)}'})

            # Update progress every 10 rows
            if (row_idx - 1) % 10 == 0:
                record.progress = int((row_idx - 1) / total_rows * 100)
                record.save(update_fields=['progress'])

        record.progress = 100
        record.success_count = success_count
        record.failed_count = failed_count
        record.duplicate_count = duplicate_count
        record.error_summary = error_summary
        
        if failed_count == 0 and success_count > 0:
            record.status = 'success'
            record.logs = '导入成功'
        elif success_count > 0 and failed_count > 0:
            record.status = 'partial'
            record.logs = '部分导入成功，请查看错误明细'
        else:
            record.status = 'failed'
            record.logs = '全部导入失败'
            
    except Exception as e:
        record.status = 'failed'
        record.logs = f"执行异常: {str(e)}\n{traceback.format_exc()}"
        
    finally:
        record.finished_at = timezone.now()
        record.save()
