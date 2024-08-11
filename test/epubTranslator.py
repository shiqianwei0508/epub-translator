import multiprocessing
import logging
import os
import argparse
import configparser
import tempfile
from ebooklib import epub
from tqdm import tqdm
from xhtmlTranslate import XHTMLTranslator

def process_chapter(item, file_path, args):
    if item.get_type() == epub.EpubHtml:
        temp_file_path = None
        output_temp_file_path = None
        try:
            original_content = item.get_body_content_str()
            logging.debug(f"处理章节: {item.get_id()}")

            # 创建临时文件以存储章节内容，并设置为自动删除
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xhtml') as temp_file:
                temp_file.write(original_content.encode('utf-8'))
                temp_file_path = temp_file.name  # 记录临时文件路径

            # 使用 XHTMLTranslator 类进行翻译
            translator = XHTMLTranslator(
                http_proxy=args.http_proxy,
                transapi_suffixes=args.transapi_suffixes,
                dest_lang=args.dest_lang,
                transMode=args.transMode,
                TranslateThreadWorkers=args.TranslateThreadWorkers
            )

            # 处理临时文件进行翻译
            output_temp_file_path = temp_file_path.replace('.xhtml', '_translated.xhtml')
            translator.process_xhtml(temp_file_path, output_temp_file_path)

            # 读取翻译后的内容
            with open(output_temp_file_path, 'r', encoding='utf-8') as translated_file:
                translated_content = translated_file.read()

            logging.debug(f"章节 {item.get_id()} 翻译成功")
            return item.get_id(), translated_content

        except Exception as e:
            logging.error(f"处理章节时出错: {e}")
            return item.get_id(), None

        finally:
            # 删除临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if output_temp_file_path and os.path.exists(output_temp_file_path):
                os.remove(output_temp_file_path)

    return None

def translate_epub(file_path, args):
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到文件: {file_path}")

        logging.debug(f"正在读取 EPUB 文件: {file_path}")
        book = epub.read_epub(file_path)

        chapters = list(book.get_items_of_type(epub.EpubHtml))

        # 创建进程池
        with multiprocessing.Pool() as pool:
            # 使用 tqdm 显示进度条
            results = list(tqdm(pool.imap(lambda item: process_chapter(item, file_path, args), chapters), total=len(chapters), desc=f"翻译进度 - {file_path}"))

        # 更新书籍中的章节内容
        for item_id, new_content in filter(None, results):
            if new_content is not None:
                item = book.get_item_with_id(item_id)
                item.set_body_content(new_content)

        # 保存修改后的 EPUB 文件
        output_file = f'translated_{os.path.basename(file_path)}'
        epub.write_epub(output_file, book)
        logging.info(f"翻译完成！已保存为: {output_file}")

    except FileNotFoundError as fnf_error:
        logging.error(fnf_error)
    except Exception as e:
        logging.error(f"发生错误: {e}")

def main(file_paths, args):
    for file_path in file_paths:
        translate_epub(file_path, args)

if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='翻译 EPUB 文件')
    parser.add_argument('file_paths', type=str, nargs='+', help='EPUB 文件路径（至少输入一个）')

    # 添加翻译参数
    parser.add_argument('--http_proxy', type=str, default=None, help='HTTP 代理（例如：http://your.proxy:port）')
    parser.add_argument('--transapi_suffixes', type=str, required=True, help='翻译 API 后缀，以逗号分隔（例如：com,com.tw,co.jp）')
    parser.add_argument('--dest_lang', type=str, required=True, help='目标语言（例如：zh-cn）')
    parser.add_argument('--transMode', type=int, choices=[1, 2], default=1, help='翻译模式（1: 仅翻译文本，2: 返回原文+翻译文本）')
    parser.add_argument('--TranslateThreadWorkers', type=int, default=16, help='翻译线程工作数（默认16）')

    args = parser.parse_args()

    # 支持配置文件读取
    config = configparser.ConfigParser()
    if os.path.exists('config.ini'):
        config.read('config.ini')
        args.http_proxy = args.http_proxy or config.get('translation', 'http_proxy', fallback=None)
        args.transapi_suffixes = args.transapi_suffixes or config.get('translation', 'transapi_suffixes', fallback=None)
        args.dest_lang = args.dest_lang or config.get('translation', 'dest_lang', fallback=None)
        args.transMode = args.transMode or config.getint('translation', 'transMode', fallback=1)
        args.TranslateThreadWorkers = args.TranslateThreadWorkers or config.getint('translation', 'TranslateThreadWorkers', fallback=16)

    # 调用主函数
    main(args.file_paths, args)