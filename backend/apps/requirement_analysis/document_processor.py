# -*- coding: utf-8 -*-
# -----------------------------
# @Author    : 影子
# @Time      : 2026/4/7 20:28
# @Software  : PyCharm
# @FileName  : document_processor.py
# -----------------------------
import re
import json
import os
from tika import parser
from django.conf import settings

from backend.config_loader import config_loader
from backend.log_config import get_logger

logger = get_logger(__name__)

get_server = config_loader.get_server_config()

# Tika 服务器超时配置（秒），从 config.yaml 读取
TIKA_TIMEOUT = get_server.get('tika_timeout', 180)  # 默认 3 分钟

def extract_text_with_tika(file_path):
    """使用 Tika 提取文件文本"""
    headers = {
        'X-Tika-OCRLanguage': get_server['doc_language'],
        'X-Tika-PDFExtractInlineImages': 'true'  # 如果是PDF，尝试提取内嵌图片进行OCR
    }
    
    # 设置请求选项，增加超时时间
    requestOptions = {
        'timeout': TIKA_TIMEOUT  # 连接和读取超时时间
    }
    
    parsed = parser.from_file(
        file_path,
        serverEndpoint=get_server['doc_parser_url'],
        headers=headers,
        service='text',
        requestOptions=requestOptions
    )
    # print(f"✅ 原始数据提取成功: {parsed}")
    content = parsed.get('content', '')
    if content and isinstance(content, bytes):
        content = content.decode('utf-8', errors='ignore')
    return content


def load_corrections(file_path):
    """加载外部纠错文件"""
    if not os.path.exists(file_path):
        # print(f"⚠️ 纠错文件不存在: {file_path}")
        logger.warning(f"⚠️ 纠错文件不存在: {file_path}")
        return {"common_errors": {}, "regex_rules": []}

    result = {"common_errors": {}, "regex_rules": []}

    if file_path.endswith('.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                result['common_errors'] = data.get('common_errors', {})
                result['regex_rules'] = data.get('regex_rules', [])
        except Exception as e:
            # print(f"❌ JSON加载失败: {e}")
            logger.error(f"❌ JSON加载失败: {e}")

    elif file_path.endswith('.txt'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith('regex:'):
                        parts = line[6:].strip().split('>>>', 1)
                        if len(parts) == 2:
                            result['regex_rules'].append({
                                "pattern": parts[0].strip(),
                                "replacement": parts[1].strip()
                            })
                    else:
                        parts = line.split('>>>', 1)
                        if len(parts) == 2:
                            result['common_errors'][parts[0].strip()] = parts[1].strip()
        except Exception as e:
            # print(f"❌ TXT加载失败: {e}")
            logger.error(f"❌ TXT加载失败: {e}")

    # print(f"加载纠错规则: {len(result['common_errors'])} 条普通规则, {len(result['regex_rules'])} 条正则规则")
    logger.info(f"加载纠错规则: {len(result['common_errors'])} 条普通规则, {len(result['regex_rules'])} 条正则规则")
    return result


def apply_corrections(text, corrections):
    """增强版纠错函数：处理跨行的OCR错误"""
    if not text or not corrections:
        return text

    common_errors = corrections.get('common_errors', {})
    for wrong, right in common_errors.items():
        text = text.replace(wrong, right)

    # 处理跨行错误
    for wrong, right in common_errors.items():
        wrong_no_space = wrong.replace(' ', '')
        if len(wrong_no_space) >= 2:
            pattern = '\\s*\\n?\\s*'.join(list(wrong_no_space))
            try:
                text = re.sub(pattern, right, text)
            except:
                pass

    regex_rules = corrections.get('regex_rules', [])
    for rule in regex_rules:
        pattern = rule.get('pattern')
        replacement = rule.get('replacement')
        if pattern and replacement:
            try:
                text = re.sub(pattern, replacement, text)
            except:
                pass
    return text


def format_list_items(text):
    """智能合并序号和内容"""
    if not text:
        return ""

    lines = text.split('\n')
    numbers = []
    contents = []
    result_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        number_match = re.match(r'^(\d+)[、\.．]?\s*$', line)
        if number_match:
            numbers.append(number_match.group(1))
        else:
            if numbers:
                content = re.sub(r'^\d+[、\.．]?\s*', '', line)
                content = re.sub(r'(\d)\s+([\u4e00-\u9fff])', r'\1\2', content)
                content = re.sub(r'([\u4e00-\u9fff])\s+(\d)', r'\1\2', content)
                contents.append(content)
            else:
                result_lines.append(line)

    if numbers and contents:
        count = min(len(numbers), len(contents))
        for i in range(count):
            result_lines.append(f"{numbers[i]}、{contents[i]}")
    return '\n'.join(result_lines)


def clean_text(raw_text, corrections=None):
    """清理从 Tika 获取的文本"""
    if not raw_text:
        return ""

    cleaned_text = re.sub(r'\n\s*\n+', '\n', raw_text)
    cleaned_text = '\n'.join(line.strip() for line in cleaned_text.splitlines())
    cleaned_text = re.sub(r'(?<=[\u4e00-\u9fff])[^^\S\n]+(?=[\u4e00-\u9fff])', '', cleaned_text)

    chinese_punctuation = r'[\u3000-\u303f\uff00-\uffef]'
    cleaned_text = re.sub(rf'([\u4e00-\u9fff])[^^\S\n]+({chinese_punctuation})', r'\1\2', cleaned_text)
    cleaned_text = re.sub(rf'({chinese_punctuation})[^^\S\n]+([\u4e00-\u9fff])', r'\1\2', cleaned_text)
    cleaned_text = re.sub(r'([\u4e00-\u9fff])[^^\S\n]+([:;,!?\.])', r'\1\2', cleaned_text)
    cleaned_text = re.sub(r':', '：', cleaned_text)
    cleaned_text = re.sub(r'\[bookmark[：:][^\]]*\]', '', cleaned_text)
    cleaned_text = format_list_items(cleaned_text)

    if corrections:
        cleaned_text = apply_corrections(cleaned_text, corrections)

    cleaned_text = re.sub(r'\n\s*\n+', '\n', cleaned_text).strip()
    return cleaned_text


def extract_text_with_tika_and_clean(file_path, correction_file=None):
    """
    提取文本并清理（支持单文件和批量处理）
    :param file_path: 单个文件路径（字符串）或文件路径列表
    :param correction_file: 纠错文件路径
    :return: 单文件：返回字符串内容  多文件：返回字典 {文件路径: 内容}
    """
    corrections = None
    if correction_file:
        if os.path.exists(correction_file):
            corrections = load_corrections(correction_file)
        else:
            logger.warning(f"纠错文件不存在: {correction_file}")
            print(f"⚠️ 纠错文件不存在: {correction_file}")

    # 判断是列表还是单个字符串
    if isinstance(file_path, (list, tuple)):
        results = {}
        total = len(file_path)

        for idx, fp in enumerate(file_path, 1):
            logger.info(f"[{idx}/{total}] 正在处理: {os.path.basename(fp)}")
            # print(f"[{idx}/{total}] 正在处理: {os.path.basename(fp)}")
            try:
                raw_content = extract_text_with_tika(fp)
                clean_content = clean_text(raw_content, corrections)
                results[fp] = clean_content
                logger.info(f"[{idx}/{total}] 处理成功: {os.path.basename(fp)}, 字符数: {len(clean_content)}")
            except Exception as e:
                logger.error(f"[{idx}/{total}] 处理失败: {fp}, 错误: {e}")
                # print(f"❌ 处理失败: {e}")
                results[fp] = f"ERROR: {str(e)}"

        logger.info(f"批量处理完成，共 {total} 个文件")
        # print(f"✅ 批量处理完成，共 {total} 个文件\n")
        return results
    else:
        # logger.info(f"正在处理文件: {os.path.basename(file_path)}")
        raw_content = extract_text_with_tika(file_path)
        clean_content = clean_text(raw_content, corrections)
        logger.info(f"文件处理完成: {os.path.basename(file_path)}, 字符数: {len(clean_content)}")
        return clean_content


def document_processor(file_list: list):
    """对外提供统一接口，输出解析并清洗后的字符串数据"""
    ocr_correction_path = settings.PATHS_OCR_CORRECTION

    logger.info(f"文档处理请求: OCR纠错文件路径={ocr_correction_path}, 输入文件数={len(file_list)}")
    print(f"OCR纠错文件路径：{ocr_correction_path}")
    print(f"输入文件列表：{file_list}")

    if not os.path.exists(ocr_correction_path):
        logger.warning(f"OCR纠错文件不存在: {ocr_correction_path}")
        print(f"⚠️ 纠错文件不存在: {ocr_correction_path}")

    results = extract_text_with_tika_and_clean(
        file_list,
        correction_file=ocr_correction_path
    )

    # 输出结果
    contents = '\n'.join(results.values())
    logger.info(f"文档处理完成，总字符数: {len(contents)}")
    print(f"✅ 清洗后的需求: {contents}")
    return contents
