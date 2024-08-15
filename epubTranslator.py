import fnmatch
import logging
import os
import random
import shutil
import sqlite3
import time
import zipfile
import configparser
import argparse
import multiprocessing

from xhtmlTranslate import XHTMLTranslator, Logger


class TranslationStatusDB:
    # 状态常量
    STATUS_PENDING = 0  # 未开始
    STATUS_IN_PROGRESS = 1  # 进行中
    STATUS_COMPLETED = 2  # 完成
    STATUS_ERROR = 3  # 异常退出

    def __init__(self, db_name='translation_status.db', db_directory='.'):
        """初始化 TranslationStatusDB 类。

        :param db_name: 数据库文件名（默认 'translation_status.db'）
        :param db_directory: 数据库文件目录（默认当前目录）
        """
        self.db_name = db_name
        self.db_directory = db_directory
        self.db_path = os.path.join(db_directory, db_name)
        # self.create_tables()

    def connect(self):
        """建立数据库连接"""
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        """创建数据表"""
        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                # 创建翻译状态表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS translation_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chapter_path TEXT NOT NULL,
                        status INTEGER NOT NULL,
                        error_message TEXT
                    )
                ''')
                # 创建状态描述表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS status_description (
                        id INTEGER PRIMARY KEY,
                        description TEXT NOT NULL
                    )
                ''')
                # 插入状态描述
                cursor.execute('DELETE FROM status_description')  # 清空表以避免重复插入
                cursor.executemany('''
                    INSERT INTO status_description (id, description) VALUES (?, ?)
                ''', [
                    (self.STATUS_PENDING, '未开始'),
                    (self.STATUS_IN_PROGRESS, '进行中'),
                    (self.STATUS_COMPLETED, '完成'),
                    (self.STATUS_ERROR, '异常退出')
                ])
                connection.commit()
        except sqlite3.Error as e:
            print(f"An error occurred while creating tables: {e}")

    def insert_status(self, chapter_path, status, error_message=None):
        """插入翻译状态

        :param chapter_path: 章节路径
        :param status: 翻译状态，应为常量
        :param error_message: 错误信息（可选）
        """
        if status not in (self.STATUS_PENDING, self.STATUS_IN_PROGRESS, self.STATUS_COMPLETED, self.STATUS_ERROR):
            raise ValueError("Invalid status value.")

        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('''
                    INSERT INTO translation_status (chapter_path, status, error_message)
                    VALUES (?, ?, ?)
                ''', (chapter_path, status, error_message))
                connection.commit()
        except sqlite3.Error as e:
            print(f"An error occurred while inserting status: {e}")

    def update_status(self, chapter_path, status, error_message=None):
        """更新翻译状态

        :param chapter_path: 章节路径
        :param status: 新的翻译状态，应为常量
        :param error_message: 错误信息（可选）
        """
        if status not in (self.STATUS_PENDING, self.STATUS_IN_PROGRESS, self.STATUS_COMPLETED, self.STATUS_ERROR):
            raise ValueError("Invalid status value.")

        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('''
                    UPDATE translation_status
                    SET status = ?, error_message = ?
                    WHERE chapter_path = ?
                ''', (status, error_message, chapter_path))
                connection.commit()
                if cursor.rowcount == 0:
                    print(f"没有找到章节 '{chapter_path}' 的记录。")
                else:
                    print(f"章节 '{chapter_path}' 的翻译状态已更新为 {status}。")
        except sqlite3.Error as e:
            print(f"An error occurred while updating status: {e}")

    def get_all_statuses(self):
        """获取所有翻译状态"""
        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('SELECT * FROM translation_status')
                rows = cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            print(f"An error occurred while fetching statuses: {e}")
            return []

    def get_status_by_chapter(self, chapter_path):
        """根据章节路径获取翻译状态"""
        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('SELECT * FROM translation_status WHERE chapter_path = ?', (chapter_path,))
                row = cursor.fetchone()
            return row
        except sqlite3.Error as e:
            print(f"An error occurred while fetching status for {chapter_path}: {e}")
            return None

    def get_status_descriptions(self):
        """获取所有状态描述"""
        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('SELECT * FROM status_description')
                rows = cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            print(f"An error occurred while fetching status descriptions: {e}")
            return []

    def get_chapters_not_completed(self):
        """获取所有翻译状态不是完成的文章列表"""
        try:
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute('SELECT chapter_path FROM translation_status WHERE status != ?',
                               (self.STATUS_COMPLETED,))
                rows = cursor.fetchall()
            return [row[0] for row in rows]  # 返回章节路径列表
        except sqlite3.Error as e:
            print(f"An error occurred while fetching articles not completed: {e}")
            return []

    def __repr__(self):
        return f"<TranslationStatusDB(db_name='{self.db_name}', db_directory='{self.db_directory}')>"


class EPUBTranslator(XHTMLTranslator):
    def __init__(self, file_paths, processes, http_proxy, log_file, log_level, gtransapi_suffixes, dest_lang,
                 trans_mode, translate_thread_workers, tags_to_translate):
        self.file_paths = file_paths
        self.processes = processes
        super(EPUBTranslator, self).__init__(http_proxy, gtransapi_suffixes, dest_lang, trans_mode, translate_thread_workers, tags_to_translate)
        # self.http_proxy = http_proxy
        # self.gtransapi_suffixes = gtransapi_suffixes
        # self.dest_lang = dest_lang
        # self.trans_mode = trans_mode
        # self.logger = logger
        # self.translate_thread_workers = translate_thread_workers
        # self.tags_to_translate = tags_to_translate

        # 实例化DB类
        translate_db = None

        # 实例化日志类
        self.logger = Logger(log_file=log_file, level=log_level)
        # self.logger = logging.getLogger(__name__)

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

            EPUBTranslator.translate_db.update_status(chapter_item, EPUBTranslator.translate_db.STATUS_COMPLETE)
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

    def translate_with_delay(self, chapter_item, index, total):

        self.logger.debug(f"Starting translation for chapter {chapter_item} use delay method")

        # 翻译章节
        self.translate_chapter(chapter_item, index, total)
        # 添加随机等待时间，范围在1到5秒之间
        wait_time = random.uniform(1, 5)
        self.logger.debug(f"Waiting for {wait_time:.2f} seconds after translating chapter {index + 1}")
        time.sleep(wait_time)

    @staticmethod
    def update_progress(current, total):
        progress = (current / total) * 100
        print()
        print(f"\nProgress: {progress:.2f}% - Translated {current} of {total} chapters.\n")

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
                self.initialize_db(db_name='translation_status.db',
                                   db_directory=epub_extracted_path)

        else:
            self.logger.info(f"extract epub to the Directory and create DB.")
            initial_work_dir(epub_extracted_path)


        chapters_not_complete = EPUBTranslator.translate_db.get_chapters_not_completed()
        self.logger.debug(f"chapters_not_complete: {chapters_not_complete}")

        total_chapters = len(chapters_not_complete)
        self.logger.debug(f"Total chapters: {total_chapters}")


        current_progress = multiprocessing.Value('i', 0)  # 共享变量

        def update_progress_callback(_):
            try:
                with current_progress.get_lock():
                    current_progress.value += 1
                    EPUBTranslator.update_progress(current_progress.value, total_chapters)
            except Exception as e:
                self.logger.error(f"Error in update_progress_callback: {e}")

        with multiprocessing.Pool(processes=self.processes) as pool:
            for index, chapter_item in enumerate(chapters_not_complete):
                self.logger.debug(f"Processing chapter: {index} {chapter_item}")
                try:
                    pool.apply_async(self.translate_with_delay, (chapter_item, index, total_chapters),
                                     callback=update_progress_callback)
                except Exception as e:
                    self.logger.error(f"Error in multiprocessing progress: {e}")
                self.logger.debug(f"Processed chapter: {index} {chapter_item} \n")

            # 等待所有进程完成
            pool.close()
            pool.join()

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
    main()
