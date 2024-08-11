import argparse
import random
import time
import logging

from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup, NavigableString
import requests
import os
from google_trans_new import google_translator

http_proxy = 'http://10.99.99.108:11110'
transapi_suffix = 'co.jp'
dest_lang = 'zh-cn'  # 目标翻译语言


def setup_logging(log_file='app.log', level=logging.DEBUG):
    """设置日志记录，输出到控制台和文件。"""
    logger = logging.getLogger()
    logger.setLevel(level)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # 创建文件处理器
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)

    # 设置日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 将处理器添加到 logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# def translate_text(text):
#     """翻译单个文本，支持字符串和字符串列表。"""
#     translator = google_translator(timeout=5, url_suffix=transapi_suffix, proxies={'http': http_proxy,
#                                                                                    'https': http_proxy})
#     max_retries = 5
#     for attempt in range(max_retries):
#         try:
#             # 记录原始文本
#             logging.debug(f"Translating text: {text}")
#             if isinstance(text, str):
#                 result = translator.translate(text, 'dest_lang')  # 替换为目标语言
#                 logging.debug(f"Translated result: {result}")
#                 return f"{text} [{result}] "  # 返回格式化的字符串
#             else:
#                 results = [translator.translate(substr, 'dest_lang') for substr in text]
#                 logging.debug(f"Translated results: {results}")
#                 return [f"{substr} [{result}] " for substr, result in zip(text, results)]  # 返回格式化的文本列表
#         except Exception as e:
#             logging.error(f"Error during translation attempt {attempt + 1}: {e}")
#             if attempt < max_retries - 1:
#                 wait_time = random.uniform(2, 7)
#                 logging.info(f"Retrying in {wait_time:.2f} seconds...")
#                 time.sleep(wait_time)
#
#     logging.warning("Translation failed after multiple attempts. Returning original text.")
#     return f"{text} [Translation failed]"  # 返回原始文本并说明翻译失败


def translate_text(text):
    """翻译单个文本，支持字符串和字符串列表。"""
    translator = google_translator(timeout=5, url_suffix=transapi_suffix, proxies={'http': http_proxy,
                                                                            'https': http_proxy})
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # 打印原始文本
            # print(f"Translating text: {text}")
            logging.debug(f"Translating text: {text}")
            if isinstance(text, str):
                result = translator.translate(text, dest_lang)
                logging.debug(f"Translated result: {result}")
                # logging.debug("\n")
                return f"{text} [{result}]"  # 返回格式化的字符串
            else:
                results = [translator.translate(substr, dest_lang) for substr in text]
                logging.debug(f"Translated results: {results}")
                # print("\n")
                return [f"{substr} [{result}]" for substr, result in zip(text, results)]  # 返回格式化的文本列表
        except Exception as e:
            logging.error(f"Error during translation attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = random.uniform(2, 7)
                logging.error(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)

    logging.warning("Translation failed after multiple attempts. Returning original text.")
    return f"{text} [Translation failed]"  # 返回原始文本并说明翻译失败



def translate_tag(tag, texts_to_translate):
    for child in tag.contents:
        if isinstance(child, NavigableString):
            if child.string.strip():
                try:
                    texts_to_translate.append((child, child.string.strip()))
                except Exception as e:
                    # print(f"Failed to add text for translation: {child.string}. Error: {e}")
                    logging.error(f"Failed to add text for translation: {child.string}. Error: {e}")
                    continue  # 如果添加失败，跳过这个文本段
        else:
            translate_tag(child, texts_to_translate)  # 递归处理子标签


def process_xhtml(input_file_path, output_file_path):
    with open(input_file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file.read(), 'lxml')

    texts_to_translate = []
    for p_tag in soup.find_all('p'):
        translate_tag(p_tag, texts_to_translate)

    translate_all(texts_to_translate)

    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(str(soup))

def translate_all(texts_to_translate):
    with ThreadPoolExecutor(max_workers=16) as executor:
        children, texts = zip(*texts_to_translate)  # Unzip the list of tuples
        try:
            for child, translated_text in zip(children, executor.map(translate_text, texts)):
                child.replace_with(translated_text)
        except Exception as exc:
            # print(f'An error occurred: {exc}')
            logging.error(f'An error occurred: {exc}')


if __name__ == "__main__":
    setup_logging()  # 设置日志记录

    parser = argparse.ArgumentParser(description='Translate an XHTML file.')
    parser.add_argument('input_file', type=str, help='The path of the XHTML file to translate.')
    args = parser.parse_args()

    input_file_path = args.input_file
    base_name, ext = os.path.splitext(input_file_path)
    output_file_path = f"{base_name}_translated{ext}"

    # process_xhtml(input_file_path, output_file_path)

    start_time = time.time()  # 记录开始时间
    process_xhtml(input_file_path, output_file_path)
    end_time = time.time()  # 记录结束时间

    execution_time = end_time - start_time  # 计算执行时间
    logging.debug(f"Execution time: {execution_time:.2f} seconds")



