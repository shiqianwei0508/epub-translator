import os
from tool_updater import ToolUpdater
from epubfile_handler import FileHandler
from translation_handler import TranslationHandler
from xhtml_handler import XHTMLHandler
from command_line_parser import CommandLineParser
from pathlib import Path

if __name__ == "__main__":
    # 检查工具更新
    ToolUpdater.check_for_updates()

    # 解析命令行参数
    args = CommandLineParser().parse()

    # 创建文件处理实例
    epub_file_path = args.epub_file_path.replace('&', '').replace('\'', '').replace('\"', '').strip()
    epub_abs_file_path = os.path.abspath(epub_file_path)

    if os.path.isfile(epub_abs_file_path) and epub_abs_file_path.endswith('.epub'):
        file_handler = FileHandler(epub_abs_file_path)
        file_handler.get_file_info()

        if file_handler.extract():
            # 创建翻译处理实例
            translator = TranslationHandler(dest_lang=args.lang) if args.lang else TranslationHandler(dest_lang='zh-cn')

            # 设置翻译字典
            if args.dict:
                translation_dict_file_path = args.dict.replace('&', '').replace('\'', '').replace('\"', '').strip()
                translator.set_dictionary(os.path.abspath(translation_dict_file_path))

            # 获取 HTML 文件路径
            html_list_path = [str(p.resolve()) for p in
                              Path(file_handler.file_extracted_path).rglob('*.[hH][tT][mM][lL]')]

            # 创建 HTML 处理实例并翻译
            html_handler = XHTMLHandler(html_list_path, translator)
            html_handler.translate_html_files()  # 翻译 HTML 文件

            # 压缩为 EPUB 文件
            file_handler.zip()
    else:
        print('EPUB file path is incorrect!')
        sys.exit()
