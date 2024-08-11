import argparse
import random
import time
import logging
import os


from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup, NavigableString
from google_trans_new import google_translator
from itertools import cycle

class Logger:
    def __init__(self, log_file='app.log', level=logging.DEBUG):
        self.logger = logging.getLogger()
        self.logger.setLevel(level)

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
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

class XHTMLTranslator:
    def __init__(self, http_proxy, transapi_suffixes, dest_lang, transMode=1, TranslateThreadWorkers=16):
        self.http_proxy = http_proxy
        self.transapi_suffixes = transapi_suffixes.split(',')
        self.dest_lang = dest_lang
        self.transMode = transMode
        # self.translator = google_translator(timeout=5, url_suffix=self.transapi_suffix, proxies={'http': self.http_proxy, 'https': self.http_proxy})
        self.TranslateThreadWorkers = TranslateThreadWorkers

        logging.debug(f"transapi_suffixes: {self.transapi_suffixes}")



    def translate_text(self, text):
        """翻译单个文本，支持字符串和字符串列表。"""
        max_retries = 8

        self.transapi_suffixes_cycle = cycle(self.transapi_suffixes)  # 使用无限循环
        logging.debug(f"transapi_suffixes_cycle: {self.transapi_suffixes_cycle}")

        self.current_suffix = next(self.transapi_suffixes_cycle)

        # 每次请求时都创建新的翻译器实例
        translator = google_translator(timeout=5, url_suffix=self.current_suffix,
                                       proxies={'http': self.http_proxy, 'https': self.http_proxy})

        for attempt in range(max_retries):
            try:
                logging.debug(f"Translating text: {text} using suffix: {self.current_suffix}")

                if isinstance(text, str):
                    result = translator.translate(text, self.dest_lang)
                    logging.debug(f"Translated result: {result}")
                    return self.format_result(text, result)
                else:
                    results = [translator.translate(substr, self.dest_lang) for substr in text]
                    logging.debug(f"Translated results: {results}")
                    return [self.format_result(substr, result) for substr, result in zip(text, results)]
            # except Exception as e:
            #     logging.error(f"Error during translation attempt {attempt + 1}: {e}")
            #     if attempt < max_retries - 1:
            #         self.current_suffix = next(self.transapi_suffixes_cycle)
            #         translator = google_translator(timeout=5, url_suffix=self.current_suffix,
            #                                        proxies={'http': self.http_proxy, 'https': self.http_proxy})
            #         wait_time = random.uniform(2, 7)
            #         logging.error(f"Retrying in {wait_time:.2f} seconds with new suffix: {self.current_suffix}...")
            #         time.sleep(wait_time)
            except Exception as e:
                logging.error(f"Error during translation attempt {attempt + 1}: {e}")
                wait_time = random.uniform(2, 7)
                if attempt < 2:
                    # 前 3 次不修改后缀
                    logging.error(f"Retrying in {wait_time:.2f} seconds without changing suffix...")
                else:
                    # 从第 4 次开始修改后缀并重建实例
                    self.current_suffix = next(self.transapi_suffixes_cycle)
                    translator = google_translator(timeout=5, url_suffix=self.current_suffix,
                                                   proxies={'http': self.http_proxy, 'https': self.http_proxy})
                    logging.error(f"Retrying in {wait_time:.2f} seconds with new suffix: {self.current_suffix}...")

                time.sleep(wait_time)

        logging.warning("Translation failed after multiple attempts. Returning original text.")
        return {"original": text, "error": "Translation failed"}


    def format_result(self, original, translated):
        """根据模式格式化翻译结果。"""
        if self.transMode == 1:
            return translated  # 仅返回翻译文本
        elif self.transMode == 2:
            return f"{original} [{translated}]"  # 返回格式化的字符串
        else:
            raise ValueError("翻译模式错误")  # 抛出翻译模式错误

    def translate_tag(self, tag, texts_to_translate):
        for child in tag.contents:
            if isinstance(child, NavigableString):
                if child.string.strip():
                    try:
                        texts_to_translate.append((child, child.string.strip()))
                    except Exception as e:
                        logging.error(f"Failed to add text for translation: {child.string}. Error: {e}")
                        continue  # 如果添加失败，跳过这个文本段
            else:
                self.translate_tag(child, texts_to_translate)  # 递归处理子标签

    def translate_all(self, texts_to_translate):
        with ThreadPoolExecutor(max_workers=self.TranslateThreadWorkers) as executor:
            children, texts = zip(*texts_to_translate)  # Unzip the list of tuples
            try:
                for child, translated_text in zip(children, executor.map(self.translate_text, texts)):
                    child.replace_with(translated_text)
            except Exception as exc:
                logging.error(f'An error occurred: {exc}')

    def process_xhtml(self, input_file_path, output_file_path):
        with open(input_file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file.read(), 'lxml')

        texts_to_translate = []
        for p_tag in soup.find_all('p'):
            self.translate_tag(p_tag, texts_to_translate)

        self.translate_all(texts_to_translate)

        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(str(soup))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate an XHTML file.')
    parser.add_argument('input_file', type=str, help='The path of the XHTML file to translate.')
    parser.add_argument('http_proxy', type=str, help='HTTP proxy address.')
    # parser.add_argument('transapi_suffix', type=str, help='Translation API suffix.')
    parser.add_argument('--transapi_suffixes', type=str, required=True,
                        help='Comma-separated list of API suffixes (e.g., "com,com.tw,co.jp,com.hk")')
    parser.add_argument('--dest_lang', type=str, default='zh-cn', help='Target translation language.')
    parser.add_argument('--transMode', type=int, choices=[1, 2], default=1,
                        help='when tranMode=1, return translated text; '
                             'when tranMode=2, return original + translated text.')
    parser.add_argument('--TranslateThreadWorkers', type=int, default=16, help='Translate Thread Workers, more big, more speed, more cpu')
    parser.add_argument('--log_file', type=str, default='app.log', help='Log file name.')
    parser.add_argument('--log_level', type=str, default='DEBUG', help='Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).')

    args = parser.parse_args()

    # 设置日志级别
    log_level = getattr(logging, args.log_level.upper(), logging.DEBUG)
    logger = Logger(log_file=args.log_file, level=log_level)

    input_file_path = args.input_file
    base_name, ext = os.path.splitext(input_file_path)
    output_file_path = f"{base_name}_translated{ext}"

    start_time = time.time()  # 记录开始时间

    translator = XHTMLTranslator(http_proxy=args.http_proxy, transapi_suffixes=args.transapi_suffixes, dest_lang=args.dest_lang, transMode=args.transMode, TranslateThreadWorkers=args.TranslateThreadWorkers)
    translator.process_xhtml(input_file_path, output_file_path)

    end_time = time.time()  # 记录结束时间
    execution_time = end_time - start_time  # 计算执行时间
    logging.info(f"Execution time: {execution_time:.2f} seconds")