import fnmatch
import logging
import os
import random
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

from xhtmlTranslate import XHTMLTranslator, Logger
from db.translation_status_db import TranslationStatusDB


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

    @staticmethod
    def create_epub_from_directory(input_dir, output_file):
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
        print(f'Created {output_file} from {input_dir}')

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

    def translate_chapter(self, chapter_item, chapter_index, total_chapters):

        self.logger.debug(f"Starting translation for chapter {chapter_index + 1}/{total_chapters}")
        EPUBTranslator.translate_db.update_status(chapter_item, EPUBTranslator.translate_db.STATUS_IN_PROGRESS)

        with open(chapter_item, 'r', encoding='utf-8') as file:
            xhtml_content = file.read()
        try:
            translated_content = self.process_xhtml(xhtml_content, self.tags_to_translate)
            if not translated_content.strip():
                raise ValueError("翻译内容为空")

            with open(chapter_item, 'w', encoding='utf-8') as file:
                file.write(translated_content)

            EPUBTranslator.translate_db.update_status(chapter_item, EPUBTranslator.translate_db.STATUS_COMPLETED)
            self.logger.debug(f"Finished translation for chapter {chapter_index + 1}/{total_chapters}")
            # return translated_content
        except ValueError as ve:
            EPUBTranslator.translate_db.update_status(chapter_item, EPUBTranslator.translate_db.STATUS_ERROR, str(ve))
            self.logger.error(f"Value error for chapter {chapter_index + 1}: {ve}")
            # return "", chapter_item # 返回空内容和chapter路径
        except Exception as e:
            EPUBTranslator.translate_db.update_status(chapter_item, EPUBTranslator.translate_db.STATUS_ERROR, str(e))
            self.logger.error(f"Error translating chapter {chapter_index + 1}: {e}")
            # return "", chapter_item # 返回空内容和chapter路径

    def translate_with_delay(self, chapter_item, index, total, log_queue):

        log_queue.put(f"Starting translation for chapter {chapter_item} use delay method")

        # 翻译章节
        self.translate_chapter(chapter_item, index, total)
        # 添加随机等待时间，范围在1到5秒之间
        wait_time = random.uniform(1, 5)
        log_queue.put(f"Waiting for {wait_time:.2f} seconds after translating chapter {index + 1}")
        time.sleep(wait_time)

    @staticmethod
    def update_progress(current, total):
        progress = (current / total) * 100

        print(f"\nProgress: {progress:.2f}% - Translated {current} of {total} chapters.\n")

    # def listener(self, log_queue):
    #     """监听进程，负责输出日志"""
    #     while True:
    #         log_message = log_queue.get()
    #         print(f'log_message: {log_message}')
    #         # self.logger.debug(repr(log_message))  # 使用类的 logger 输出日志
    #         if log_message is None:  # 用 None 来结束监听
    #             break

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
            except Exception as e:
                self.logger.error(f"Error Create db : {e}")

            try:
                # 把所有章节路径写入数据库
                for chapter_path in chapters:
                    # 尝试使用 utf-8 编码插入数据
                    EPUBTranslator.translate_db.insert_status(chapter_path, EPUBTranslator.translate_db.STATUS_PENDING)
            except Exception as e:
                self.logger.error(f"Error insert chapter translation status: {e}")

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
        self.logger.debug(f"Total chapters: {total_chapters}")

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
                    future = executor.submit(self.translate_with_delay, chapter_item, index, total_chapters, log_queue)
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

        EPUBTranslator.create_epub_from_directory(epub_extracted_path, f"{base_name}_translated.epub")

        # 清理临时目录
        # shutil.rmtree(epub_extracted_path)

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
