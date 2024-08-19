import fnmatch
import logging
import os
import random
import re
import shutil
import signal
import sys
import time
import zipfile
import configparser
import argparse
import concurrent.futures
import queue
import threading

from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle

from bs4 import BeautifulSoup, NavigableString
from translation_api.google_trans_new import google_translator
from tqdm import tqdm

from xhtmlTranslate import XHTMLTranslator, Logger
from db.translation_status_db import TranslationStatusDB
from languageDetect import detect_language


def signal_handler(sig, frame):
    print("程序被中断，正在清理...")
    # 执行任何必要的清理操作
    # 例如，可以设置一个标志位来通知线程停止工作
    sys.exit(0)


class EPUBTranslator(XHTMLTranslator):
    # 定义类属性
    translate_db = None

    def __init__(self, file_paths, processes, http_proxy, log_file, log_level, gtransapi_suffixes, dest_lang,
                 trans_mode, translate_thread_workers, tags_to_translate):
        self.file_paths = file_paths
        self.processes = processes
        super(EPUBTranslator, self).__init__(http_proxy, gtransapi_suffixes, dest_lang,
                                             trans_mode, translate_thread_workers, tags_to_translate)

        self.gtransapi_suffixes = gtransapi_suffixes.split(',')
        self.gtransapi_suffixes_cycle = cycle(self.gtransapi_suffixes)  # 使用无限循环

        # 实例化日志类
        self.logger = Logger(log_file=log_file, level=log_level)

    @classmethod
    def initialize_db(cls, db_name='translation_status.db', db_directory='.'):
        """
        初始化数据库，修改类属性translate_db为TranslationStatusDB类的实例化
        """
        cls.translate_db = TranslationStatusDB(db_name=db_name, db_directory=db_directory)

    @staticmethod
    def extract_epub(epub_file, output_dir):

        try:
            with zipfile.ZipFile(epub_file, 'r') as zip_ref:
                zip_ref.extractall(output_dir)
            logging.info(f'Extracted {epub_file} to {output_dir}')

        except FileNotFoundError:
            logging.error(f'The file {epub_file} does not exist.')
        except zipfile.BadZipFile:
            logging.error(f'The file {epub_file} is not a zip file or it is corrupted.')
        except Exception as e:
            logging.error(f'An error occurred while extracting {epub_file}: {e}')

    def create_epub_from_directory(self, input_dir, output_file):
        # 确保 output_file 是字符串类型
        if isinstance(output_file, bytes):
            output_file = output_file.decode('utf-8')  # 转换为字符串

        # 先创建一个新的 EPUB 文件
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            # 只写入 mimetype 文件，确保它是第一个文件且不压缩
            zip_ref.write(os.path.join(input_dir, 'mimetype'), 'mimetype', compress_type=zipfile.ZIP_STORED)

            # 遍历目录，写入所有其他文件
            for foldername, subfolders, filenames in os.walk(input_dir):
                for filename in filenames:
                    if filename == 'mimetype':
                        continue  # 跳过 mimetype 文件，避免重复添加
                    # 计算相对路径
                    file_path = os.path.join(foldername, filename)

                    # 确保file_path为字符串
                    if isinstance(file_path, bytes):
                        file_path = file_path.decode('utf-8')  # 转换为字符串
                    # 添加文件到 ZIP
                    zip_ref.write(file_path, os.path.relpath(file_path, input_dir))
        self.logger.info(f"Created '{output_file}' from '{input_dir}'")

    @staticmethod
    def find_xhtml_files(directory):
        xhtml_files = []

        extensions = ['*.html', '*.xhtml']  # 定义要查找的扩展名列表

        # 遍历指定的目录
        for dirpath, dirnames, filenames in os.walk(directory):
            for ext in extensions:  # 遍历扩展名列表
                matches = fnmatch.filter(filenames, ext)
                for filename in matches:
                    # 构造绝对路径
                    absolute_path = os.path.join(dirpath, filename)
                    xhtml_files.append(absolute_path)

        return xhtml_files

    def translate_text(self, text):
        """翻译单个文本，支持字符串和字符串列表。"""
        max_retries = 5

        # 每次请求时都创建获取当前前缀并且创建新的翻译器实例
        current_suffix = next(self.gtransapi_suffixes_cycle)
        translatorObj = google_translator(timeout=5, url_suffix=current_suffix,
                                          proxies={'http': self.http_proxy, 'https': self.http_proxy})

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Translating text: {text} using suffix: {current_suffix}")

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
                    current_suffix = next(self.gtransapi_suffixes_cycle)
                    translatorObj = google_translator(timeout=5, url_suffix=current_suffix,
                                                      proxies={'http': self.http_proxy, 'https': self.http_proxy})
                    self.logger.error(f"Retrying in {wait_time:.2f} seconds with new suffix: {current_suffix}...")

                time.sleep(wait_time)

        self.logger.critical("Translation failed after multiple attempts. Returning None.")
        return None

    def process_xhtml(self, chapter_item, supported_tags):

        with open(chapter_item, 'r', encoding='utf-8') as file:
            xhtml_content = file.read()

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
                    texts_to_translate.append((element, need_translate))  # 存储原始元素和文本`

        # 使用 ThreadPoolExecutor 进行并发翻译
        with ThreadPoolExecutor(max_workers=self.TranslateThreadWorkers) as executor:
            # 使用 tqdm 显示进度条
            future_to_text = {executor.submit(self.translate_text, text): (element, text) for element, text in
                              texts_to_translate}
            self.logger.debug(f"Total texts to translate: {len(future_to_text)}")

            for future in tqdm(as_completed(future_to_text), total=len(future_to_text),
                               desc=f"Translating the chapter '{chapter_item}'"):
                element, original_text = future_to_text[future]
                # time.sleep(random.uniform(0.1, 1))  # 随机等待时间，0.1到1秒
                self.logger.debug(f"Processing translation for: '{original_text}' (Element: {element})")

                translated_text = future.result()
                self.logger.debug(f"Received translation for: '{original_text}': {translated_text}")

                # 如果 translated_text 为空，直接返回，不再处理此文本
                if translated_text is None or translated_text == "":
                    self.logger.warning(f"Translated text is empty for '{original_text}'. Skipping to next.")
                    return {"error": f"Translation error for '{chapter_item}'"}  # 返回错误信息

                translations.append((element, translated_text))  # 存储原始元素和翻译结果
                self.logger.debug(f"Successfully translated '{original_text}' to '{translated_text}'")

        # 统一替换翻译结果
        for element, translated_text in translations:
            element.replace_with(translated_text)
            self.logger.debug(f"Replaced with translated text: '{translated_text}'")

        self.logger.debug(f"Finished translation of chapter '{chapter_item}'.")
        with open(chapter_item, 'w', encoding='utf-8') as file:
            file.write(str(soup))
        # return str(soup)

    def translate_chapter(self, chapter_item):

        self.logger.info(f"Starting translation for chapter {chapter_item}")
        EPUBTranslator.translate_db.update_status(chapter_item, EPUBTranslator.translate_db.STATUS_IN_PROGRESS)

        # try:
        translated_result = self.process_xhtml(chapter_item, self.tags_to_translate)

        if isinstance(translated_result, dict) and "error" in translated_result:
            self.logger.error(f"Failed to translate '{chapter_item}': {translated_result['error']}")
            EPUBTranslator.translate_db.update_status(chapter_item, EPUBTranslator.translate_db.STATUS_ERROR,
                                                      translated_result['error'])
        else:
            EPUBTranslator.translate_db.update_status(chapter_item, EPUBTranslator.translate_db.STATUS_COMPLETED)
            self.logger.info(f"Finished translation for chapter {chapter_item}")

    def translate_with_delay(self, chapter_item, index, log_queue):

        log_queue.put(f"Starting translation for chapter {chapter_item} use delay method")

        # 检测文档是否已翻译

        with open(chapter_item, 'r', encoding='utf-8') as file:
            chapter_text = file.read()

        # if contains_chinese(chapter_text):
        if detect_language(chapter_text) == self.dest_lang:
            self.logger.info(f"The chapter {chapter_item} seems to be translated already.")
            EPUBTranslator.translate_db.update_status(chapter_item, EPUBTranslator.translate_db.STATUS_COMPLETED)
        else:
            # 翻译章节
            self.translate_chapter(chapter_item)
            # 添加随机等待时间，范围在1到5秒之间
            wait_time = random.uniform(1, 5)
            log_queue.put(f"Waiting for {wait_time:.2f} seconds after translating chapter {index + 1}")
            time.sleep(wait_time)

    @staticmethod
    def update_progress(current, total):
        progress = (current / total) * 100

        print(f"\nProgress: {progress:.2f}% - Translated {current} of {total} chapters.\n")

    def listener(self, log_queue):
        while True:
            log_entry = log_queue.get()
            if log_entry == "DONE":
                break
            self.logger.debug(repr(log_entry))  # 使用类的 logger 输出日志

    def process_epub(self, epub_path):
        """
        处理epub文件
        :param epub_path:  提供epub文件的路径

        处理步骤：
        1. 解压 EPUB 文件到临时目录。
        2. 遍历所有 XHTML 文件并返回一个包含所有 XHTML 绝对路径的列表。
        3. 创建 SQLite 数据库，并将所有章节的路径插入到数据库中，状态设为 "未开始"。
        4. 查询所有状态为 '未开始' 的章节路径，并将这些路径放入 `chapters_not_complete` 列表中。
        5. 使用多进程并行处理所有未完成的章节。
        6. 从临时目录创建新的 EPUB 文件。
        7. 成功翻译之后，删除临时目录
        """
        base_name = os.path.splitext(epub_path)[0]
        epub_extracted_path = f"{base_name}_translated"

        def initial_work_dir(tmp_path):
            # 创建新的输出目录
            os.makedirs(tmp_path, exist_ok=True)  # exist_ok=True，确保如果目录已存在不会抛出异常

            EPUBTranslator.extract_epub(epub_path, tmp_path)
            xhtml_files = EPUBTranslator.find_xhtml_files(tmp_path)

            # self.logger.debug(f"xhtml_files: {xhtml_files}")
            self.logger.debug(f"Extracted {len(xhtml_files)} xhtml files")

            chapters = xhtml_files

            if not chapters:
                self.logger.error(f"No chapters extracted from {epub_path}. Skipping file.")
                return

            # 创建 SQLite 数据库
            try:
                self.initialize_db(db_name='translation_status.db',
                                   db_directory=epub_extracted_path)
                EPUBTranslator.translate_db.create_tables()
            except Exception as db_e:
                self.logger.error(f"Error Create db : {db_e}")

            try:
                # 把所有章节路径写入数据库
                for chapter_path in chapters:
                    # 尝试使用 utf-8 编码插入数据
                    EPUBTranslator.translate_db.insert_status(chapter_path, EPUBTranslator.translate_db.STATUS_PENDING)
            except Exception as db_e:
                self.logger.error(f"Error insert chapter translation status: {db_e}")

            self.logger.info(f'Created SQLite database in {tmp_path}')

        # 检查输出目录是否存在
        if os.path.exists(epub_extracted_path):
            # 提示用户确认是否删除
            confirm = input(f"The directory '{epub_extracted_path}' already exists. Do you want to delete it? (y/n): ")
            if confirm.lower() == 'y':
                shutil.rmtree(epub_extracted_path)  # 直接删除目录及其所有内容

                # 初始化
                initial_work_dir(epub_extracted_path)
            else:
                self.logger.info(f"use the exist Directory and DB")
                EPUBTranslator.initialize_db(db_name='translation_status.db', db_directory=epub_extracted_path)

        else:
            self.logger.info(f"extract epub to the Directory and create DB.")
            initial_work_dir(epub_extracted_path)

        chapters_not_complete = EPUBTranslator.translate_db.get_chapters_not_completed()
        self.logger.debug(f"chapters_not_complete: {chapters_not_complete}")

        total_chapters = len(chapters_not_complete)
        self.logger.info(f"Total chapters that need to be translate: {total_chapters}")

        # log_queue = multiprocessing.Queue()  # 创建日志队列
        #
        # listener_process = multiprocessing.Process(target=self.listener, args=(log_queue,))
        # listener_process.start()  # 启动监听进程

        log_queue = queue.Queue()  # 使用线程安全的队列
        # 启动监听线程
        listener_thread = threading.Thread(target=self.listener, args=(log_queue,))
        listener_thread.start()

        # # 多进程
        # current_progress = multiprocessing.Value('i', 0)
        #
        # def update_progress_callback(_):
        #     try:
        #         with current_progress.get_lock():
        #             current_progress.value += 1
        #             EPUBTranslator.update_progress(current_progress.value, total_chapters)
        #     except Exception as e:
        #         self.logger.error(f"Error in update_progress_callback: {e}")
        #
        # with multiprocessing.Pool(processes=self.processes) as pool:
        #     for index, chapter_item in enumerate(chapters_not_complete):
        #         # self.logger.debug(f"Processing chapter: {index} {chapter_item}")
        #         log_queue.put(f"Processing chapter: {index} {chapter_item}")
        #         try:
        #             pool.apply_async(self.translate_with_delay, (chapter_item, index, total_chapters, log_queue),
        #                              callback=update_progress_callback)
        #         except Exception as e:
        #             # self.logger.error(f"Error in multiprocessing progress: {e}")
        #             log_queue.put(f"Error in multiprocessing progress: {e}")
        #         log_queue.put(f"Processed chapter: {index} {chapter_item} \n")
        #
        #     # 等待所有进程完成
        #     pool.close()
        #     pool.join()

        # # 单进程处理
        # for index, chapter_item in enumerate(chapters_not_complete):
        #     # self.logger.debug(f"Processing chapter: {index} {chapter_item}")
        #     log_queue.put(f"Processing chapter: {index} {chapter_item}")
        #     try:
        #         # 直接调用翻译函数，而不是使用 apply_async
        #         self.translate_with_delay(chapter_item, index, total_chapters, log_queue)
        #         # 更新进度
        #         EPUBTranslator.update_progress(index + 1, total_chapters)
        #     except Exception as e:
        #         # self.logger.error(f"Error in single process progress: {e}")
        #         log_queue.put(f"Error in single process progress: {e}")
        #
        #     log_queue.put(f"Processed chapter: {index} {chapter_item} \n")

        # log_queue.put(None)  # 用 None 来结束监听进程
        # listener_process.join()  # 等待监听进程结束

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.processes) as executor:
            futures = []
            for index, chapter_item in enumerate(chapters_not_complete):
                log_queue.put(f"Processing chapter: {index} {chapter_item}")
                try:
                    # 提交任务到线程池
                    future = executor.submit(self.translate_with_delay, chapter_item, index, log_queue)
                    futures.append((future, index))  # 保留 future 和索引
                except Exception as e:
                    log_queue.put(f"Error in threading progress: {e}")

            # 等待所有线程完成并更新进度
            for future, index in futures:
                try:
                    future.result()  # 等待线程执行完成
                    EPUBTranslator.update_progress(index + 1, total_chapters)  # 更新进度
                except Exception as e:
                    log_queue.put(f"Error in future result: {e}")

            # 处理完所有章节
            for index, chapter_item in enumerate(chapters_not_complete):
                log_queue.put(f"Processed chapter: {index} {chapter_item}")

        # 结束监听线程
        log_queue.put("DONE")  # 发送结束信号
        listener_thread.join()  # 等待监听线程结束

        # 再检查一次未翻译章节
        chapters_not_complete = EPUBTranslator.translate_db.get_chapters_not_completed()

        if len(chapters_not_complete) == 0:
            self.logger.info(f"恭喜全部章节翻译完成！")
            self.create_epub_from_directory(epub_extracted_path, f"{base_name}_translated.epub")

            # 清理临时目录
            try:
                self.logger.debug(f"开始清理临时目录")

                # 关闭数据库链接
                EPUBTranslator.translate_db.close()

                # 删除目录
                shutil.rmtree(epub_extracted_path)
                self.logger.debug(f"清理完成")
            except Exception as e:
                self.logger.error(f"临时目录清理异常: {e}")
        else:
            self.logger.critical(f"还有{len(chapters_not_complete)}个章节，没有翻译或者存在异常")
            self.logger.critical(f"没有翻译的章节是 {chapters_not_complete}")
            self.logger.critical(f"请切换代理服务器，然后，重新执行 python epubTranslator.py")
            self.logger.critical(f"本程序将会重新读取未翻译章节，直到全部翻译完成！")
            self.logger.critical(f"注意： 下次启动之后，会询问你是否删除目录，如果不想从头翻译的话，请选择'n'！")

    def translate(self):
        for epub_path in self.file_paths:
            self.logger.debug(f"Processing EPUB file: {epub_path}")
            self.process_epub(epub_path)


class ConfigLoader:
    def __init__(self, config_file, args):
        self.config_file = config_file
        self.args = args
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config.read_file(f)
            except UnicodeDecodeError:
                logging.error("Failed to decode the config file. Please check the file encoding.")
                # 这里可以选择使用其他编码重试
                with open(self.config_file, 'r', encoding='gbk') as f:
                    self.config.read_file(f)

    def get_config(self):
        """获取配置参数"""
        try:
            config_data = {
                'gtransapi_suffixes': self.config.get('Translation', 'gtransapi_suffixes', fallback=None),
                'tags_to_translate': self.config.get('Translation', 'tags_to_translate', fallback=None),
                'dest_lang': self.config.get('Translation', 'dest_lang', fallback=None),
                'http_proxy': self.config.get('Translation', 'http_proxy', fallback=None),
                'transMode': self.config.getint('Translation', 'transMode', fallback=self.args.transMode),
                'TranslateThreadWorkers': self.config.getint('Translation', 'TranslateThreadWorkers',
                                                             fallback=self.args.TranslateThreadWorkers),
                'processes': self.config.getint('Translation', 'processes', fallback=self.args.processes),
                'log_file': self.config.get('Logger', 'log_file', fallback=self.args.log_file),
                'log_level': self.config.get('Logger', 'log_level', fallback=self.args.log_level),
                # 'file_paths': self.args.file_paths
                'file_paths': [
                    path.strip() for path in
                    self.config.get('Files', 'epub_file_path', fallback="").split(',')
                    if path.strip()
                ]
            }

            # 如果需要处理文件路径为原始字符串，可以在这里进行转换
            config_data['file_paths'] = [r"{}".format(path) for path in config_data['file_paths']]

            # print(f"config_data: {config_data}")

            return config_data
        except Exception as e:
            print(f"读取配置时出错: {e}")
            return None


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='翻译 EPUB 文件')
    parser.add_argument('file_paths', type=str, nargs='*', help='EPUB 文件路径（至少输入一个）')
    parser.add_argument('--http_proxy', type=str, help='HTTP 代理（例如：http://your.proxy:port）')
    parser.add_argument('--gtransapi_suffixes', type=str,
                        help='Comma-separated list of API suffixes (e.g., "com,com.tw,co.jp,com.hk")')
    parser.add_argument('--dest_lang', type=str, help='目标语言（例如：zh-cn）')
    parser.add_argument('--transMode', type=int, choices=[1, 2], default=1,
                        help='翻译模式（1: 仅翻译文本，2: 返回原文+翻译文本）')
    parser.add_argument('--TranslateThreadWorkers', type=int, default=16, help='翻译线程工作数（默认16）')
    parser.add_argument('--processes', type=int, default=4, help='epub章节并行处理进程数（默认4）')
    parser.add_argument('--log_file', type=str, default='app.log', help='日志文件路径（默认: app.log）')
    parser.add_argument('--log_level', type=str, default='INFO', help='Log '
                                                                      'level (DEBUG, INFO, WARNING, ERROR, CRITICAL).')
    parser.add_argument('--tags_to_translate', type=str,
                        help='The content of the tags that will be translate'
                             ' (e.g., "h1,h2,h3,title,p")')

    # 首先解析命令行参数
    args = parser.parse_args()

    # 读取配置文件
    config_loader = ConfigLoader('config.ini', args)
    config = config_loader.get_config()

    # 检查配置文件中是否包含所有必需参数
    if (config.get('gtransapi_suffixes') and config.get('dest_lang') and
            config.get('http_proxy')):
        # 如果配置文件包含所有必需参数，忽略命令行参数
        pass
    else:
        # 如果缺少参数，则从命令行参数中获取
        config['gtransapi_suffixes'] = config.get('gtransapi_suffixes') or args.gtransapi_suffixes
        config['dest_lang'] = config.get('dest_lang') or args.dest_lang
        config['http_proxy'] = config.get('http_proxy') or args.http_proxy

    # 检查必需参数
    if not config['gtransapi_suffixes'] or not config['dest_lang']:
        parser.error("缺少必需的参数: --gtransapi_suffixes 和 --dest_lang")

    # 使用已存在的Logger类
    # 设置日志级别
    log_level = getattr(logging, config['log_level'].upper(), logging.DEBUG)
    # logger = Logger(log_file=config['log_file'], level=log_level)

    # 创建并运行翻译器
    translator = EPUBTranslator(
        config['file_paths'],
        config['processes'],
        config['http_proxy'],
        config['log_file'],
        log_level,
        config['gtransapi_suffixes'],
        config['dest_lang'],
        config['transMode'],
        config['TranslateThreadWorkers'],  # 确保传递翻译线程工作数
        config['tags_to_translate']
    )

    # 进行翻译
    translator.translate()


if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    main()
