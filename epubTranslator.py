import fnmatch
import logging
import os
import zipfile
import configparser
import argparse
import multiprocessing

from xhtmlTranslate import XHTMLTranslator, Logger


class EPUBTranslator:
    def __init__(self, file_paths, processes, http_proxy, gtransapi_suffixes, dest_lang,
                 trans_mode, logger, translate_thread_workers):
        self.file_paths = file_paths
        self.processes = processes
        self.http_proxy = http_proxy
        self.gtransapi_suffixes = gtransapi_suffixes
        self.dest_lang = dest_lang
        self.trans_mode = trans_mode
        self.logger = logger
        self.translate_thread_workers = translate_thread_workers

    @staticmethod
    def extract_epub(epub_file, output_dir):
        with zipfile.ZipFile(epub_file, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        logging.debug(f'Extracted {epub_file} to {output_dir}')
        # return output_dir

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

        # 遍历指定的目录
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in fnmatch.filter(filenames, '*.xhtml'):
                # 构造绝对路径
                absolute_path = os.path.join(dirpath, filename)
                # xhtml_files.append((filename, absolute_path))
                xhtml_files.append(absolute_path)

        return xhtml_files

    def translate_chapter(self, chapter_item, chapter_index, total_chapters):
        self.logger.debug(f"Starting translation for chapter {chapter_index + 1}/{total_chapters}")
        with open(chapter_item, 'r', encoding='utf-8') as file:
            xhtml_content = file.read()
        try:
            translator = XHTMLTranslator(http_proxy=self.http_proxy, gtransapi_suffixes=self.gtransapi_suffixes,
                                         dest_lang=self.dest_lang, transMode=self.trans_mode,
                                        TranslateThreadWorkers=self.translate_thread_workers,
                                         logger=self.logger)
            translated_content = translator.process_xhtml(xhtml_content)
            if not translated_content.strip():
                raise ValueError("翻译内容为空")

            with open(chapter_item, 'w', encoding='utf-8') as file:
                file.write(translated_content)

            self.logger.debug(f"Finished translation for chapter {chapter_index + 1}/{total_chapters}")
            # return translated_content
        except ValueError as ve:
            self.logger.error(f"Value error for chapter {chapter_index + 1}: {ve}")
            # return "", chapter_item # 返回空内容和chapter路径
        except Exception as e:
            self.logger.error(f"Error translating chapter {chapter_index + 1}: {e}")
            # return "", chapter_item # 返回空内容和chapter路径

    def update_progress(self, current, total):
        progress = (current / total) * 100
        print(f"Progress: {progress:.2f}% - Translated {current} of {total} chapters.")

    def process_epub(self, epub_path):
        """
        处理epub文件
        :param epub_path:  提供epub文件的路径

        处理步骤：
        1. 使用extract_epub方法解压epub文件到`os.path.splitext(epub_path)[0]_translated`目录中
        2. 遍历所有xhtml文件
        3. 使用translate_chapter方法翻译xhtml文件，并修改
        4. 压缩为'os.path.splitext(epub_path)[0]_translated.epub'文件
        """
        base_name = os.path.splitext(epub_path)[0]
        epub_extracted_path = f"{base_name}_translated"

        EPUBTranslator.extract_epub(epub_path, epub_extracted_path)
        xhtml_files = EPUBTranslator.find_xhtml_files(epub_extracted_path)
        self.logger.debug(f"xhtml_files: {xhtml_files}")
        self.logger.debug(f"Extracted {len(xhtml_files)} xhtml files")

        chapters = xhtml_files
        if not chapters:
            self.logger.error(f"No chapters extracted from {epub_path}. Skipping file.")
            return

        total_chapters = len(chapters)

        with multiprocessing.Pool(processes=self.processes) as pool:
            for index, chapter_item in enumerate(chapters):
                self.logger.debug(f"index: {index}, chapter: {chapter_item}")
                pool.apply_async(self.translate_chapter, (chapter_item, index, total_chapters),
                                 callback=lambda _: self.update_progress(index + 1, total_chapters))

            # 等待所有进程完成
            pool.close()
            pool.join()

        EPUBTranslator.create_epub_from_directory(epub_extracted_path, f"{base_name}_translated.epub")

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
            'TranslateThreadWorkers': self.config.getint('Translation',
                                                         'TranslateThreadWorkers',
                                                         fallback=self.args.TranslateThreadWorkers),
            'processes': self.config.getint('Translation', 'processes', fallback=self.args.processes),
            'log_file': self.config.get('Logger', 'log_file', fallback=self.args.log_file),
            'log_level': self.config.get('Logger', 'log_level', fallback=self.args.log_level),
            # 'file_paths': self.args.file_paths
            'file_paths': [path.strip() for path in self.config.get('Files',
                                                                    'epub_file_path',
                                                                    fallback=self.args.file_paths).split(',')]
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
