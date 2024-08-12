import os
import sys
import configparser
import logging
import argparse
import multiprocessing
from ebooklib import epub
from bs4 import BeautifulSoup
from xhtmlTranslate import XHTMLTranslator, Logger

class EPUBTranslator:
    def __init__(self, file_paths, processes, http_proxy, transapi_suffixes, dest_lang, trans_mode, logger):
        self.file_paths = file_paths
        self.processes = processes
        self.http_proxy = http_proxy
        self.transapi_suffixes = transapi_suffixes
        self.dest_lang = dest_lang
        self.trans_mode = trans_mode
        self.logger = logger


    def extract_chapters(self, epub_path):
        self.logger.debug(f"Extracting chapters from: {epub_path}")
        try:
            # 读取EPUB文件
            book = epub.read_epub(epub_path)
            chapters = []

            # 获取所有项目
            items = book.get_items()
            self.logger.debug(f"Items found in the book: {[item.get_id() for item in items]}")

            # 遍历所有项目，寻找EpubHtml类型的章节
            for item in items:
                if isinstance(item, epub.EpubHtml):
                    chapters.append(item)
                    self.logger.debug(f"Found chapter: {item.get_id()} - Title: {item.get_title()}")

            self.logger.debug(f"Extracted {len(chapters)} chapters from: {epub_path}")
            return chapters
        except Exception as e:
            self.logger.error(f"Error extracting chapters from {epub_path}: {e}")
            return []


    def translate_chapter(self, chapter_item, chapter_index, total_chapters):
        self.logger.debug(f"Starting translation for chapter {chapter_index + 1}/{total_chapters}")
        try:
            translator = XHTMLTranslator(self.http_proxy, self.transapi_suffixes, self.dest_lang, self.trans_mode)
            translated_content = translator.translate(chapter_item.get_body_content_str())
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
        for translated_content, chapter_id in translated_chapters:
            if translated_content:  # 只更新非空的翻译内容
                chapter_item = book.get_item_with_id(chapter_id)
                chapter_item.set_body_content(translated_content)
                self.logger.debug(f"Updated chapter with ID {chapter_id}")
            else:
                self.logger.warning(f"Skipping update for chapter ID {chapter_id} due to empty translated content.")

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

            translated_chapters = [result.get() for result in results]

        # 更新EPUB文件中的章节
        book = epub.read_epub(epub_path)
        self.update_chapters(book, translated_chapters)

        # 保存更新后的EPUB文件，使用原文件名加 "_translated"
        base_name = os.path.splitext(epub_path)[0]
        new_epub_path = f"{base_name}_translated.epub"
        try:
            epub.write_epub(new_epub_path, book)
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
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.args = args

    def get_config(self):
        # 从命令行参数或配置文件中获取所有参数
        http_proxy = self.args.http_proxy or self.config.get('translation', 'http_proxy', fallback=None)
        transapi_suffixes = self.args.transapi_suffixes or self.config.get('translation', 'transapi_suffixes',
                                                                           fallback=None)
        dest_lang = self.args.dest_lang or self.config.get('translation', 'dest_lang', fallback=None)
        trans_mode = self.args.transMode or self.config.getint('translation', 'transMode', fallback=1)
        translate_thread_workers = self.args.TranslateThreadWorkers or self.config.getint('translation',
                                                                                          'TranslateThreadWorkers',
                                                                                          fallback=16)

        file_paths = self.args.file_paths if self.args.file_paths else self.config.get('files', 'epub_file_path',
                                                                                       fallback=None).split(',')
        processes = self.args.processes or self.config.getint('files', 'processes', fallback=4)

        log_file = self.args.log_file or self.config.get('Logger', 'log_file', fallback='app.log')

        # 打印配置以进行调试
        print(
            f"Config loaded: {http_proxy}, {transapi_suffixes}, {dest_lang}, {trans_mode}, {translate_thread_workers}, {file_paths}, {processes}, {log_file}")

        return {
            "file_paths": file_paths,
            "processes": processes,
            "http_proxy": http_proxy,
            "transapi_suffixes": transapi_suffixes.split(','),
            "dest_lang": dest_lang,
            "trans_mode": trans_mode,
            "translate_thread_workers": translate_thread_workers,
            "log_file": log_file
        }


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='翻译 EPUB 文件')
    parser.add_argument('file_paths', type=str, nargs='*', help='EPUB 文件路径（至少输入一个）')

    # 添加翻译参数
    parser.add_argument('--http_proxy', type=str, default=None, help='HTTP 代理（例如：http://your.proxy:port）')
    parser.add_argument('--transapi_suffixes', type=str, help='翻译 API 后缀，以逗号分隔（例如：com,com.tw,co.jp）')
    parser.add_argument('--dest_lang', type=str, help='目标语言（例如：zh-cn）')
    parser.add_argument('--transMode', type=int, choices=[1, 2], default=1, help='翻译模式（1: 仅翻译文本，2: 返回原文+翻译文本）')
    parser.add_argument('--TranslateThreadWorkers', type=int, default=16, help='翻译线程工作数（默认16）')
    parser.add_argument('--processes', type=int, default=4, help='并行进程数（默认4）')
    parser.add_argument('--log_file', type=str, default='app.log', help='日志文件路径（默认: app.log）')

    args = parser.parse_args()

    # 支持配置文件读取
    config_loader = ConfigLoader('config.ini', args)
    config = config_loader.get_config()

    # 检查必需参数
    if not config['transapi_suffixes'] or not config['dest_lang']:
        parser.error("缺少必需的参数: --transapi_suffixes 和 --dest_lang")

    # 使用已存在的Logger类
    logger = Logger(config['log_file'])
    translator = EPUBTranslator(config['file_paths'], config['processes'], config['http_proxy'],
                                config['transapi_suffixes'], config['dest_lang'], config['trans_mode'], logger)
    translator.translate()


if __name__ == "__main__":
    main()