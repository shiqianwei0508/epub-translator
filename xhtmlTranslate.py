import argparse
import random
import re
import shutil
import signal
import time
import logging
import os
import sys


from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup, NavigableString
from itertools import cycle
from tqdm import tqdm
from custom_logger import Logger

from translate_api.google_translate_v2 import google_translator
from translate_api.zhipuai_translate_v1 import ZhipuAiTranslate


# 定义信号处理函数
def signal_handler(sig, frame):
    print("程序被中断，正在清理...")
    # 执行任何必要的清理操作
    # 例如，可以设置一个标志位来通知线程停止工作
    sys.exit(0)


class XHTMLTranslator:
    def __init__(self, http_proxy, gtransapi_suffixes, dest_lang, transMode=1,
                 TranslateThreadWorkers=16, tags_to_translate="title,h1,h2,p",
                 translator_api='google', **translator_kwargs):
        # 设置 logger
        self.logger = logging.getLogger(__name__)
        
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

        # 指定翻译API
        self.translator_api = translator_api
        # 存储额外的翻译器参数
        self.translator_kwargs = translator_kwargs

        self.logger.debug(f"translator_api: {self.translator_api}")
        self.logger.debug(f"translator_kwargs: {self.translator_kwargs}")

    def get_translator_class(self):
        # 根据translator_api返回对应的翻译类
        if self.translator_api == 'zhipu':
            return ZhipuAiTranslate
        elif self.translator_api == 'google':
            return google_translator
        else:
            raise ValueError(f"Unsupported translator API: {self.translator_api}")

    # def create_translator_instance(self):
    #     # 获取翻译类
    #     translator_class = self.get_translator_class()
    #     # 根据翻译类和参数创建实例
    #     return translator_class(**self.translator_kwargs)

    def translate_text_common(self, text):
        """翻译单个文本，支持字符串和字符串列表。"""
        max_retries = 3

        translator_class = self.get_translator_class()
        self.logger.debug(f"translator_class: {translator_class}")

        translatorObj = translator_class(**self.translator_kwargs)

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Translating text: {text} at {attempt} time")

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
                time.sleep(wait_time)

        self.logger.critical("Translation failed after multiple attempts. Returning original text.")
        return {"original": text, "error": "Translation failed"}


    def translate_text_google(self, text):
        """翻译单个文本，支持字符串和字符串列表。"""
        max_retries = 5

        translator_class = self.get_translator_class()
        self.logger.debug(f"translator_class: {translator_class}")

        # 每次请求时都创建获取当前前缀并且创建新的翻译器实例
        self.current_suffix = next(self.gtransapi_suffixes_cycle)
        translatorObj = translator_class(timeout=5, url_suffix=self.current_suffix,
                                          proxies={'http': self.http_proxy, 'https': self.http_proxy})
        # 创建翻译器实例

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
                    translatorObj = translator_class(timeout=5, url_suffix=self.current_suffix,
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
        
    def process_xhtml(self, chapter_item, supported_tags):

        with open(chapter_item, 'r', encoding='utf-8') as file:
            xhtml_content = file.read()

        soup = BeautifulSoup(xhtml_content, 'html.parser')
        self.logger.debug("Starting translation of paragraphs.")

        # 支持翻译的标签
        supported_tags = self.tags_to_translate
        translations = []  # 存储待替换的文本与翻译结果

        # 将 soup.descendants 转换为列表，以避免在遍历过程中修改结构
        descendants = list(soup.descendants)

        # 收集需要翻译的文本和对应的元素
        texts_to_translate = []
        for element in descendants:
            # if isinstance(element, NavigableString) and element.strip() and element.parent.name in supported_tags:
            if isinstance(element, NavigableString) and element.parent.name in supported_tags:
                # 检查元素是否包含字母且不只是数字
                if re.search(r'[a-zA-Z]', element) and not re.match(r'^\d+$', element):
                    need_translate = element.strip()
                    texts_to_translate.append((element, need_translate))  # 存储原始元素和文本
        # self.logger.debug(f"texts_to_translate: {texts_to_translate}")

        # 使用 ThreadPoolExecutor 进行并发翻译
        with ThreadPoolExecutor(max_workers=self.TranslateThreadWorkers) as executor:
            # 使用 tqdm 显示进度条
            if self.translator_api == 'google':
                future_to_text = {executor.submit(self.translate_text_google, text): (element, text) for element, text in
                                  texts_to_translate}
            else:
                future_to_text = {executor.submit(self.translate_text_common, text): (element, text) for element, text in
                                  texts_to_translate}

            self.logger.debug(f"Total texts to translate: {len(future_to_text)}")

            for future in tqdm(as_completed(future_to_text), total=len(future_to_text),
                               desc=f"Translating the chapter '{chapter_item}'"):
                element, original_text = future_to_text[future]
                # time.sleep(random.uniform(0.1, 1))  # 随机等待时间，0.1到1秒
                self.logger.debug(f"Processing translation for: '{original_text}' (Element: {element})")

                translated_text = future.result()
                self.logger.debug(f"Received translation for: '{original_text}': {translated_text}")

                # if isinstance(translated_text, dict) and "error" in translated_text:
                #     self.logger.error(f"Failed to translate '{original_text}': {translated_text['error']}")
                #     continue

                # 如果 translated_text 为空，直接返回，不再处理此文本
                if translated_text is None or translated_text == "":
                    self.logger.warning(f"Translated text is empty for '{original_text}'. Skipping to next.")
                    return {"error": f"Translation error for '{chapter_item}'"}  # 返回错误信息

                translations.append((element, translated_text))  # 存储原始元素和翻译结果
                self.logger.debug(f"Successfully translated '{original_text}' to '{translated_text}'")

        # 统一替换翻译结果
        # for element, translated_text in translations:
        #     try:
        #         element.replace_with(translated_text)
        #         self.logger.debug(f"Replaced with translated text: '{translated_text}'")
        #     except Exception as e:
        #         self.logger.warning(f"Error during translation of paragraphs: {e}")

        for element, translated_text in translations:
            try:
                element.replace_with(translated_text)
                self.logger.debug(f"Replaced with translated text: '{translated_text}'")
            except AttributeError as e:
                self.logger.warning(f"Invalid element: {element}. Skipping. ")
                self.logger.warning(f"The data class of the element: {type(element)}")
                self.logger.warning(f"The data class of the translated text: {type(translated_text)}")
                self.logger.warning(f"Error details: {e}")
                continue
            except Exception as e:
                self.logger.warning(f"Error during translation of paragraphs: {e}")

        self.logger.debug(f"Finished translation of chapter '{chapter_item}'.")
        with open(chapter_item, 'w', encoding='utf-8') as file:
            file.write(str(soup))




        #     self.logger.debug(f"Total texts to translate: {len(future_to_text)}")
        #
        #     for future in tqdm(as_completed(future_to_text), total=len(future_to_text), desc="Translating a chapter"):
        #         element, original_text = future_to_text[future]
        #         # time.sleep(random.uniform(0.1, 1))  # 随机等待时间，0.1到1秒
        #         self.logger.debug(f"Processing translation for: '{original_text}' (Element: {element})")
        #         try:
        #             translated_text = future.result()
        #             self.logger.debug(f"Received translation for: '{original_text}': {translated_text}")
        #             if isinstance(translated_text, dict) and "error" in translated_text:
        #                 self.logger.error(f"Failed to translate '{original_text}': {translated_text['error']}")
        #                 continue
        #
        #             # 如果 translated_text 为空，跳过当前循环
        #             if translated_text is None or translated_text == "":
        #                 self.logger.warning(f"Translated text is empty for '{original_text}'. Skipping to next.")
        #                 continue
        #
        #             translations.append((element, translated_text))  # 存储原始元素和翻译结果
        #             self.logger.debug(f"Successfully translated '{original_text}' to '{translated_text}'")
        #         except Exception as e:
        #             self.logger.error(f"Translation error for text '{original_text}': {str(e)}")
        #             self.logger.debug(f"Future state: {future}")
        #             self.logger.debug(f"Exception details: {e}", exc_info=True)
        #
        # # 统一替换翻译结果
        # for element, translated_text in translations:
        #     element.replace_with(translated_text)
        #     self.logger.debug(f"Replaced with translated text: '{translated_text}'")
        #
        # self.logger.debug("Finished translation of paragraphs.")
        # # return str(soup)
        # with open(chapter_item, 'w', encoding='utf-8') as file:
        #     file.write(str(soup))


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
    parser.add_argument('--translator_api', type=str, default='google', help='Translate API, support google and zhipuAI')
    parser.add_argument('--zhipu_api_key', type=str, help='ZhiPu API key.')
    parser.add_argument('--zhipu_translate_timeout', type=int, help='ZhiPu translate timeout.')

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
    translator = XHTMLTranslator(http_proxy=args.http_proxy,
                                 gtransapi_suffixes=args.gtransapi_suffixes,
                                 dest_lang=args.dest_lang,
                                 transMode=args.transMode,
                                 TranslateThreadWorkers=args.TranslateThreadWorkers,
                                 tags_to_translate=args.tags_to_translate,
                                 translator_api=args.translator_api,
                                 zhipu_api_key=args.zhipu_api_key,
                                 zhipu_translate_timeout=args.zhipu_translate_timeout
                                 )

    # log all parameters in the object translator
    logger.debug(f"translator parameters: {translator.__dict__}")

    # # begin to translate
    # translated_content = translator.process_xhtml(xhtml_content, args.tags_to_translate)



    # Write the output to a new file
    base_name, ext = os.path.splitext(args.input_file)
    output_file_path = f"{base_name}_translated{ext}"
    # with open(output_file_path, 'w', encoding='utf-8') as file:
    #     file.write(translated_content)

    if os.path.exists(output_file_path):
        os.remove(output_file_path)

    shutil.copyfile(input_file_path, output_file_path)

    # begin to translate
    translator.process_xhtml(output_file_path, args.tags_to_translate)

    # End time counter
    end_time = time.time()
    execution_time = end_time - start_time  # Calculate execution time

    logger.info(f"Translation completed. Output saved to: {output_file_path}")
    logger.info(f"Execution time: {execution_time:.2f} seconds")
