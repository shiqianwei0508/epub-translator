import argparse
import random
import re
import signal
import time
import logging
import os
import sys


from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup, NavigableString
from google_trans_new import google_translator
from itertools import cycle
from tqdm import tqdm

# 定义信号处理函数
def signal_handler(sig, frame):
    print("程序被中断，正在清理...")
    # 执行任何必要的清理操作
    # 例如，可以设置一个标志位来通知线程停止工作
    sys.exit(0)



class ColoredFormatter(logging.Formatter):
    # 定义颜色
    COLORS = {
        'DEBUG': '\033[94m',     # 蓝色
        'INFO': '\033[92m',      # 绿色
        'WARNING': '\033[93m',   # 黄色
        'ERROR': '\033[91m',     # 红色
        'CRITICAL': '\033[41m',  # 红色背景
        'RESET': '\033[0m',      # 重置颜色
    }

    def format(self, record):
        # 获取日志级别
        level_name = record.levelname
        # 获取对应颜色
        color = self.COLORS.get(level_name, self.COLORS['RESET'])
        # 设置记录的消息为彩色
        record.msg = f"{color}{record.msg}{self.COLORS['RESET']}"
        return super().format(record)


class Logger:
    def __init__(self, log_file='app.log', level=logging.DEBUG):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # 创建文件处理器，并设置为覆盖模式
        file_handler = logging.FileHandler(log_file, mode='w', encoding="utf-8")  # 使用 'w' 模式清空文件
        file_handler.setLevel(level)

        # 设置控制台处理器格式为 ColoredFormatter
        console_formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        # 设置文件处理器格式为普通的 Formatter
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        # 将处理器添加到 logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)


class XHTMLTranslator:
    def __init__(self, http_proxy, gtransapi_suffixes, dest_lang, transMode=1, TranslateThreadWorkers=16, logger=None,
                 tags_to_translate="title,h1,h2,p"):
        # 设置 logger
        self.logger = logger or logging.getLogger(__name__)
        
        self.http_proxy = http_proxy
        
        self.dest_lang = dest_lang
        self.transMode = transMode
        self.TranslateThreadWorkers = TranslateThreadWorkers
        self.gtransapi_suffixes = gtransapi_suffixes.split(',')
        self.gtransapi_suffixes_cycle = cycle(self.gtransapi_suffixes)  # 使用无限循环

        self.tags_to_translate = tags_to_translate.split(',')

        self.logger.debug(f"http_proxy: {self.http_proxy}")
        self.logger.debug(f"dest_lang: {self.dest_lang}")
        self.logger.debug(f"TransMode: {self.transMode}")
        self.logger.debug(f"TranslateThreadWorkers: {self.TranslateThreadWorkers}")
        self.logger.debug(f"gtransapi_suffixes: {self.gtransapi_suffixes}")
        self.logger.debug(f"gtransapi_suffixes_cycle: {self.gtransapi_suffixes_cycle}")
        self.logger.debug(f"tags_to_translate: {self.tags_to_translate}")

    def translate_text(self, text):
        """翻译单个文本，支持字符串和字符串列表。"""
        max_retries = 8

        # 每次请求时都创建获取当前前缀并且创建新的翻译器实例
        self.current_suffix = next(self.gtransapi_suffixes_cycle)
        translatorObj = google_translator(timeout=5, url_suffix=self.current_suffix,
                                          proxies={'http': self.http_proxy, 'https': self.http_proxy})

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Translating text: {text} using suffix: {self.current_suffix}")

                if isinstance(text, str):
                    result = translatorObj.translate(text, self.dest_lang)
                    self.logger.debug(f"Translated result: {result}")
                    return self.format_result(text, result)
                else:
                    results = [translatorObj.translate(substr, self.dest_lang) for substr in text]
                    self.logger.debug(f"Translated results: {results}")
                    return [self.format_result(substr, result) for substr, result in zip(text, results)]
            except Exception as e:
                self.logger.warning(f"Error during translation attempt {attempt + 1}: {e}")
                wait_time = random.uniform(2, 7)
                if attempt < 2:
                    # 前 3 次不修改后缀
                    self.logger.warning(f"Retrying in {wait_time:.2f} seconds without changing suffix...")
                else:
                    # 从第 4 次开始修改后缀并重建实例
                    self.current_suffix = next(self.gtransapi_suffixes_cycle)
                    translatorObj = google_translator(timeout=5, url_suffix=self.current_suffix,
                                                      proxies={'http': self.http_proxy, 'https': self.http_proxy})
                    self.logger.error(f"Retrying in {wait_time:.2f} seconds with new suffix: {self.current_suffix}...")

                time.sleep(wait_time)

        self.logger.critical("Translation failed after multiple attempts. Returning original text.")
        return {"original": text, "error": "Translation failed"}

    def format_result(self, original, translated):
        """根据模式格式化翻译结果。"""
        if self.transMode == 1:
            return translated  # 仅返回翻译文本
        elif self.transMode == 2:
            return f"{original} [{translated}]"  # 返回格式化的字符串
        else:
            raise ValueError("翻译模式错误")  # 抛出翻译模式错误
        
    def process_xhtml(self, xhtml_content, supported_tags):

        soup = BeautifulSoup(xhtml_content, 'html.parser')
        self.logger.debug("Starting translation of paragraphs.")

        # 支持翻译的标签
        # supported_tags = ["p", "title", "h1", "h2"]
        supported_tags = self.tags_to_translate
        translations = []  # 存储待替换的文本与翻译结果

        # 将 soup.descendants 转换为列表，以避免在遍历过程中修改结构
        descendants = list(soup.descendants)

        # 收集需要翻译的文本和对应的元素
        texts_to_translate = []
        for element in descendants:
            if isinstance(element, NavigableString) and element.strip() and element.parent.name in supported_tags:
                # 检查元素是否包含字母且不只是数字
                if re.search(r'[a-zA-Z]', element) and not re.match(r'^\d+$', element):
                    need_translate = element.strip()
                    texts_to_translate.append((element, need_translate))  # 存储原始元素和文本
        # self.logger.debug(f"texts_to_translate: {texts_to_translate}")

        # 使用 ThreadPoolExecutor 进行并发翻译
        with ThreadPoolExecutor(max_workers=self.TranslateThreadWorkers) as executor:
            # 使用 tqdm 显示进度条
            future_to_text = {executor.submit(self.translate_text, text): (element, text) for element, text in
                              texts_to_translate}
            self.logger.debug(f"Total texts to translate: {len(future_to_text)}")

            for future in tqdm(as_completed(future_to_text), total=len(future_to_text), desc="Translating a chapter"):
                element, original_text = future_to_text[future]
                # time.sleep(random.uniform(0.1, 1))  # 随机等待时间，0.1到1秒
                self.logger.debug(f"Processing translation for: '{original_text}' (Element: {element})")
                try:
                    translated_text = future.result()
                    self.logger.debug(f"Received translation for: '{original_text}': {translated_text}")
                    if isinstance(translated_text, dict) and "error" in translated_text:
                        self.logger.error(f"Failed to translate '{original_text}': {translated_text['error']}")
                        continue

                    translations.append((element, translated_text))  # 存储原始元素和翻译结果
                    self.logger.info(f"Successfully translated '{original_text}' to '{translated_text}'")
                except Exception as e:
                    self.logger.error(f"Translation error for text '{original_text}': {str(e)}")
                    self.logger.debug(f"Future state: {future}")
                    self.logger.debug(f"Exception details: {e}", exc_info=True)

        # 统一替换翻译结果
        for element, translated_text in translations:
            element.replace_with(translated_text)
            self.logger.debug(f"Replaced with translated text: '{translated_text}'")

        self.logger.debug("Finished translation of paragraphs.")
        return str(soup)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate an XHTML file.')
    parser.add_argument('input_file', type=str, help='The path of the XHTML file to translate.')
    parser.add_argument('http_proxy', type=str, help='HTTP proxy address.')
    parser.add_argument('--gtransapi_suffixes', type=str, required=True,
                        help='Comma-separated list of API suffixes (e.g., "com,com.tw,co.jp,com.hk")')
    parser.add_argument('--dest_lang', type=str, default='zh-cn', help='Target translation language.')
    parser.add_argument('--transMode', type=int, choices=[1, 2], default=1,
                        help='when tranMode=1, return translated text; '
                             'when tranMode=2, return original + translated text.')
    parser.add_argument('--TranslateThreadWorkers', type=int, default=16, help='Translate Thread Workers, '
                                                                               'more big, more speed, more cpu')
    parser.add_argument('--log_file', type=str, default='app.log', help='Log file name.')
    parser.add_argument('--log_level', type=str, default='DEBUG', help='Log level '
                                                                       '(DEBUG, INFO, WARNING, ERROR, CRITICAL).')
    parser.add_argument('--tags_to_translate', type=str, required=True,
                        help='The content of the tags that will be translate'
                             ' (e.g., "h1,h2,h3,title,p")')

    args = parser.parse_args()

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)

    # 设置日志级别
    log_level = getattr(logging, args.log_level.upper(), logging.DEBUG)
    logger = Logger(log_file=args.log_file, level=log_level)

    input_file_path = args.input_file

    start_time = time.time()

    # Read the input file
    with open(args.input_file, 'r', encoding='utf-8') as file:
        xhtml_content = file.read()

    # Process the XHTML content
    translator = XHTMLTranslator(http_proxy=args.http_proxy, gtransapi_suffixes=args.gtransapi_suffixes,
                                 dest_lang=args.dest_lang, transMode=args.transMode,
                                 TranslateThreadWorkers=args.TranslateThreadWorkers,
                                 logger=logger)
    translated_content = translator.process_xhtml(xhtml_content)

    # Write the output to a new file
    base_name, ext = os.path.splitext(args.input_file)
    output_file_path = f"{base_name}_translated{ext}"
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(translated_content)

    # End time counter
    end_time = time.time()
    execution_time = end_time - start_time  # Calculate execution time

    logger.info(f"Translation completed. Output saved to: {output_file_path}")
    logger.info(f"Execution time: {execution_time:.2f} seconds")
