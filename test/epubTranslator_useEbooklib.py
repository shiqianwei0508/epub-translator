import os
# import sys
import configparser
# import logging
import argparse
import multiprocessing

import ebooklib
from ebooklib import epub
# from ebooklib.epub import EpubWriter

from xhtmlTranslate import XHTMLTranslator, Logger
# from MyEbooklibPlugins import doNothingBeforeWirteEpub


import warnings
# 忽略特定警告
warnings.filterwarnings("ignore", category=UserWarning, module='ebooklib')
warnings.filterwarnings("ignore", category=FutureWarning, module='ebooklib')

# class CustomEpubWriter(EpubWriter):
#     def process(self):
#         # 直接跳过处理，不进行任何修改
#         pass
#
#     def _write_items(self):
#         # 直接写入书籍内容而不进行任何修改
#         for item in self.book.get_items():
#             self.out.writestr('%s/%s' % (self.book.FOLDER_NAME, item.file_name), item.get_content())

class EPUBTranslator:
    def __init__(self, file_paths, processes, http_proxy, gtransapi_suffixes, dest_lang, trans_mode, logger, translate_thread_workers):
        self.file_paths = file_paths
        self.processes = processes
        self.http_proxy = http_proxy
        self.gtransapi_suffixes = gtransapi_suffixes
        self.dest_lang = dest_lang
        self.trans_mode = trans_mode
        self.logger = logger
        self.translate_thread_workers = translate_thread_workers


    def extract_chapters(self, epub_path):
        self.logger.debug(f"Extracting chapters from: {epub_path}")
        try:
            # 读取EPUB文件
            book = epub.read_epub(epub_path)

            chapters = []
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    chapters.append(item)
                    self.logger.debug(f"Found chapter: {item.get_id()} - Name: {item.get_name()}")

            self.logger.debug(f"Extracted {len(chapters)} chapters from: {epub_path}")
            return chapters
        except Exception as e:
            self.logger.error(f"Error extracting chapters from {epub_path}: {e}")
            return []


    def translate_chapter(self, chapter_item, chapter_index, total_chapters):
        self.logger.debug(f"Starting translation for chapter {chapter_index + 1}/{total_chapters}")
        try:
            translator = XHTMLTranslator(http_proxy=self.http_proxy, gtransapi_suffixes=self.gtransapi_suffixes,
                                         dest_lang=self.dest_lang, transMode=self.trans_mode,
                                        TranslateThreadWorkers=self.translate_thread_workers,
                                         logger=self.logger)
            translated_content = translator.process_xhtml(chapter_item.get_content())
            if not translated_content.strip():
                raise ValueError("翻译内容为空")
            self.logger.debug(f"Finished translation for chapter {chapter_index + 1}/{total_chapters}")
            return translated_content, chapter_item.get_id()
        except ValueError as ve:
            self.logger.error(f"Value error for chapter {chapter_index + 1}: {ve}")
            return "", chapter_item.get_id()
        except Exception as e:
            self.logger.error(f"Error translating chapter {chapter_index + 1}: {e}")
            return "", chapter_item.get_id()  # 返回空内容和章节ID


    def update_chapters(self, book, translated_chapters):
        self.logger.info("Starting to update chapters.")

        for translated_content, chapter_id in translated_chapters:
            self.logger.debug(
                f"Processing chapter ID {chapter_id} with translated content length: {len(translated_content) if translated_content else 0}")

            if translated_content:  # 只更新非空的翻译内容
                try:
                    chapter_item = book.get_item_with_id(chapter_id)
                    if chapter_item:
                        chapter_item.set_content(translated_content)
                        self.logger.debug(
                            f"Successfully updated chapter with ID {chapter_id}. Translated content (first 50 chars): {translated_content[:1000]}...")
                    else:
                        self.logger.warning(f"Chapter ID {chapter_id} not found in the book.")
                except Exception as e:
                    self.logger.error(f"Failed to update chapter ID {chapter_id}: {e}.")
                    self.logger.debug(f"Error details: {str(e)}")
            else:
                self.logger.warning(f"Skipping update for chapter ID {chapter_id} due to empty translated content.")

        self.logger.info("Finished updating chapters.")


    def update_progress(self, current, total):
        progress = (current / total) * 100
        print(f"Progress: {progress:.2f}% - Translated {current} of {total} chapters.")

    def process_epub(self, epub_path):
        chapters = self.extract_chapters(epub_path)
        if not chapters:
            self.logger.error(f"No chapters extracted from {epub_path}. Skipping file.")
            return

        total_chapters = len(chapters)

        with multiprocessing.Pool(processes=self.processes) as pool:
            results = []
            for index, chapter_item in enumerate(chapters):
                result = pool.apply_async(self.translate_chapter, (chapter_item, index, total_chapters))
                results.append(result)

                # 更新进度
                self.update_progress(index + 1, total_chapters)

            translated_chapters = [result.get() for result in results]

        # 更新EPUB文件中的章节
        book = epub.read_epub(epub_path)
        self.update_chapters(book, translated_chapters)

        self.logger.debug(f"Items found in the translated book: {[item.get_id() for item in 
                                                       book.get_items_of_type(ebooklib.ITEM_DOCUMENT)]}")

        # 保存更新后的EPUB文件，使用原文件名加 "_translated"
        base_name = os.path.splitext(epub_path)[0]
        new_epub_path = f"{base_name}_translated.epub"
        self.logger.debug(f"Saving translated epub to {new_epub_path}")
        try:
            # epub.write_epub(new_epub_path, book, {"plugins": [doNothingBeforeWirteEpub()]})
            epub.write_epub(new_epub_path, book, {"epub3_pages": False})
            # writer = CustomEpubWriter(new_epub_path, book)
            # writer.write()
            self.logger.debug(f"Saved updated EPUB file as: {new_epub_path}")
        except Exception as e:
            self.logger.error(f"Error saving updated EPUB file {new_epub_path}: {e}")


    def translate(self):
        for epub_path in self.file_paths:
            self.logger.debug(f"Processing EPUB file: {epub_path}")
            try:
                self.process_epub(epub_path)
            except Exception as e:
                self.logger.error(f"Error processing EPUB file {epub_path}: {e}")


class ConfigLoader:
    def __init__(self, config_file, args):
        self.config_file = config_file
        self.args = args
        self.config = configparser.ConfigParser()
        self.load_config()

    # def load_config(self):
    #     """加载配置文件"""
    #     if os.path.exists(self.config_file):
    #         self.config.read(self.config_file)

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config.read_file(f)
            except UnicodeDecodeError:
                print("Failed to decode the config file. Please check the file encoding.")
                # 这里可以选择使用其他编码重试
                with open(self.config_file, 'r', encoding='gbk') as f:
                    self.config.read_file(f)

    def get_config(self):
        """获取配置参数"""
        config_data = {
            'gtransapi_suffixes': self.config.get('Translation', 'gtransapi_suffixes', fallback=None),
            'dest_lang': self.config.get('Translation', 'dest_lang', fallback=None),
            'http_proxy': self.config.get('Translation', 'http_proxy', fallback=None),
            'transMode': self.config.getint('Translation', 'transMode', fallback=self.args.transMode),
            'TranslateThreadWorkers': self.config.getint('Translation', 'TranslateThreadWorkers', fallback=self.args.TranslateThreadWorkers),
            'processes': self.config.getint('Translation', 'processes', fallback=self.args.processes),
            'log_file': self.config.get('Logger', 'log_file', fallback=self.args.log_file),
            'log_level': self.config.get('Logger', 'log_level', fallback=self.args.log_level),
            # 'file_paths': self.args.file_paths
            'file_paths': [path.strip() for path in self.config.get('Files', 'epub_file_path', fallback=self.args.file_paths).split(',')]
        }
        return config_data


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
    logger = Logger(config['log_file'])

    # 创建并运行翻译器
    translator = EPUBTranslator(
        config['file_paths'],
        config['processes'],
        config['http_proxy'],
        config['gtransapi_suffixes'],
        config['dest_lang'],
        config['transMode'],
        logger,
        config['TranslateThreadWorkers']  # 确保传递翻译线程工作数
    )

    # 进行翻译
    translator.translate()


if __name__ == "__main__":
    main()