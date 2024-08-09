import argparse
import os
import re
import shutil
import sys
import zipfile
import time
import random
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing import Pool
from pathlib import Path

import requests
import tqdm
from bs4 import BeautifulSoup
from bs4 import element
from google_trans_new import google_translator

TOOL_VERSION = '1.1.0'
LINE_SIZE = 90
HEADERS = {
    'user-agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.95 Safari/537.36')}

LANGUAGES = {
    'af': 'afrikaans',
    'sq': 'albanian',
    'am': 'amharic',
    'ar': 'arabic',
    'hy': 'armenian',
    'az': 'azerbaijani',
    'eu': 'basque',
    'be': 'belarusian',
    'bn': 'bengali',
    'bs': 'bosnian',
    'bg': 'bulgarian',
    'ca': 'catalan',
    'ceb': 'cebuano',
    'ny': 'chichewa',
    'zh-cn': 'chinese (simplified)',
    'zh-tw': 'chinese (traditional)',
    'co': 'corsican',
    'hr': 'croatian',
    'cs': 'czech',
    'da': 'danish',
    'nl': 'dutch',
    'en': 'english',
    'eo': 'esperanto',
    'et': 'estonian',
    'tl': 'filipino',
    'fi': 'finnish',
    'fr': 'french',
    'fy': 'frisian',
    'gl': 'galician',
    'ka': 'georgian',
    'de': 'german',
    'el': 'greek',
    'gu': 'gujarati',
    'ht': 'haitian creole',
    'ha': 'hausa',
    'haw': 'hawaiian',
    'iw': 'hebrew',
    'he': 'hebrew',
    'hi': 'hindi',
    'hmn': 'hmong',
    'hu': 'hungarian',
    'is': 'icelandic',
    'ig': 'igbo',
    'id': 'indonesian',
    'ga': 'irish',
    'it': 'italian',
    'ja': 'japanese',
    'jw': 'javanese',
    'kn': 'kannada',
    'kk': 'kazakh',
    'km': 'khmer',
    'ko': 'korean',
    'ku': 'kurdish (kurmanji)',
    'ky': 'kyrgyz',
    'lo': 'lao',
    'la': 'latin',
    'lv': 'latvian',
    'lt': 'lithuanian',
    'lb': 'luxembourgish',
    'mk': 'macedonian',
    'mg': 'malagasy',
    'ms': 'malay',
    'ml': 'malayalam',
    'mt': 'maltese',
    'mi': 'maori',
    'mr': 'marathi',
    'mn': 'mongolian',
    'my': 'myanmar (burmese)',
    'ne': 'nepali',
    'no': 'norwegian',
    'or': 'odia',
    'ps': 'pashto',
    'fa': 'persian',
    'pl': 'polish',
    'pt': 'portuguese',
    'pa': 'punjabi',
    'ro': 'romanian',
    'ru': 'russian',
    'sm': 'samoan',
    'gd': 'scots gaelic',
    'sr': 'serbian',
    'st': 'sesotho',
    'sn': 'shona',
    'sd': 'sindhi',
    'si': 'sinhala',
    'sk': 'slovak',
    'sl': 'slovenian',
    'so': 'somali',
    'es': 'spanish',
    'su': 'sundanese',
    'sw': 'swahili',
    'sv': 'swedish',
    'tg': 'tajik',
    'ta': 'tamil',
    'tt': 'tatar',
    'te': 'telugu',
    'th': 'thai',
    'tr': 'turkish',
    'tk': 'turkmen',
    'uk': 'ukrainian',
    'ur': 'urdu',
    'ug': 'uyghur',
    'uz': 'uzbek',
    'vi': 'vietnamese',
    'cy': 'welsh',
    'xh': 'xhosa',
    'yi': 'yiddish',
    'yo': 'yoruba',
    'zu': 'zulu',
}


class pcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    ORANGE = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def check_for_tool_updates():
    try:
        release_api = 'https://api.github.com/repos/quantrancse/epub-translator/releases/latest'
        response = requests.get(
            release_api, headers=HEADERS, timeout=5).json()
        latest_release = response['tag_name'][1:]
        if TOOL_VERSION != latest_release:
            print(
                f'Current tool version: {pcolors.FAIL}{TOOL_VERSION}{pcolors.ENDC}')
            print(
                f'Latest tool version: {pcolors.GREEN}{latest_release}{pcolors.ENDC}')
            print(
                f'Please upgrade the tool at: {pcolors.CYAN}https://github.com/quantrancse/epub-translator/releases{pcolors.ENDC}')
            print('-' * LINE_SIZE)
    except Exception:
        print('Something was wrong. Can not get the tool latest update!')


class TranslatorEngine():
    def __init__(self):
        # 构造函数，初始化属性
        self.dest_lang = 'zh-cn'  # 目标翻译语言
        self.file_path = ''  # EPUB 文件路径
        self.file_name = ''  # EPUB 文件名称
        self.file_extracted_path = ''  # EPUB 解压路径
        self.html_list_path = []  # HTML 文件路径列表
        self.translation_dict = {}  # 翻译字典
        self.translation_dict_file_path = ''  # 翻译字典文件路径
        self.dict_format = '^[^:]+:[^:]+$'  # 翻译字典格式
        self.max_trans_words = 5000  # 最大翻译字数

    def get_epub_file_info(self, file_path):
        """获取 EPUB 文件信息，包括路径和名称，创建解压路径。"""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"The file {file_path} does not exist.")
        self.file_path = file_path
        self.file_name = os.path.splitext(os.path.basename(file_path))[0]
        self.file_extracted_path = os.path.join(
            os.path.abspath(os.path.join(file_path, os.pardir)),
            self.file_name + '_translated'
        )

        # 检查 _translated 目录是否存在
        if os.path.exists(self.file_extracted_path):
            try:
                # 如果存在，删除该目录及其内容
                shutil.rmtree(self.file_extracted_path)
            except Exception as e:
                print(f"Error deleting the existing directory: {e}")

        # 重新创建翻译目录
        os.makedirs(self.file_extracted_path)

    def extract_epub(self):
        """解压 EPUB 文件。"""
        try:
            with zipfile.ZipFile(self.file_path, 'r') as zip:
                print('Extracting the epub file...', end='\r')
                zip.extractall(self.file_extracted_path)
                print(f'Extracting the epub file: [{pcolors.GREEN} DONE {pcolors.ENDC}]')
            return True
        except Exception as e:
            print(f'Extracting the epub file: [{pcolors.FAIL} FAIL {pcolors.ENDC}] - {e}')
            return False

    def get_epub_html_path(self):
        """获取解压后 EPUB 文件中的 HTML 文件路径。"""
        for file_type in ['*.[hH][tT][mM][lL]', '*.[xX][hH][tT][mM][lL]', '*.[hH][tT][mM]']:
            # 查找指定类型的 HTML 文件，并将绝对路径添加到 html_list_path 列表中
            self.html_list_path += [str(p.resolve())
                                    for p in list(Path(self.file_extracted_path).rglob(file_type))]


    def replace_translation_dict(self, text):
        """根据翻译字典替换文本中的内容。"""
        if self.translation_dict:
            for replace_text in self.translation_dict.keys():
                if replace_text in text:
                    text = text.replace(replace_text, self.translation_dict[replace_text])
        return text

    def get_translation_dict_contents(self):
        """读取翻译字典文件，并填充翻译字典。"""
        if os.path.isfile(self.translation_dict_file_path) and self.translation_dict_file_path.endswith('.txt'):
            print('Translation dictionary detected.')
            with open(self.translation_dict_file_path, encoding='utf-8') as f:
                for line in f.readlines():
                    if re.match(self.dict_format, line):
                        split = line.rstrip().split(':')
                        self.translation_dict[split[0]] = split[1]
                    else:
                        print(f'Translation dictionary is not in correct format: {line}')
                        return False
        else:
            print('Translation dictionary file path is incorrect!')
            return False
        return True

    def combine_words(self, text_list):
        """将文本列表合并分割为适合翻译的块。"""
        combined_text = []
        combined_single = ''

        for text in text_list:
            randomMaxTransWords = random.randint(30, self.max_trans_words)  # 示例：设置较小的最大字数

            combined_single += text + '  _____  '  # 添加文本和分隔符
            # print(f"combined_single : {combined_single}")

            # 检查合并后的长度是否超过随机最大翻译字数
            if len(combined_single) >= randomMaxTransWords:
                combined_text.append(combined_single)
                combined_single = ''  # 重置 combined_single 为下一个块

        # 如果最后仍有未添加的文本，确保将其添加
        if combined_single:
            combined_text.append(combined_single)

        return combined_text

    def has_notranslate(self, element):
        """检查元素是否包含 notranslate 字样"""
        return any('notranslate' in str(ele).lower() for ele in element.parents)

    def translate_html(self, xml_file):
        """翻译 XML 文件中的文本并写回文件，同时保留翻译前后的内容。"""
        try:
            # 打开了一个 HTML 文件，并将文件内容读入一个文件对象 f
            with open(xml_file, encoding='utf-8') as f:
                # 使用 BeautifulSoup 库解析了文件内容。'xml' 参数指定了解析器类型
                soup = BeautifulSoup(f, 'xml')
                # 提取所有的子元素，并将它们存入了一个列表 epub_eles
                epub_eles = list(soup.descendants)

                # text_list = []
                # for ele in epub_eles:
                #     # 判断当前元素是否是一个文本元素，并且这个元素的文本内容不是空字符串或者 'html'
                #     if isinstance(ele, element.NavigableString) and str(ele).strip() not in ['', 'html']:
                #         # 将当前元素的文本内容添加到 text_list 中
                #         text_list.append(str(ele))

                # 提取所有文本元素内容，排除含有 notranslate 的标签
                text_list = [str(ele) for ele in epub_eles
                             if isinstance(ele, element.NavigableString)
                             and str(ele).strip() not in ['', 'html']
                             and not self.has_notranslate(ele)
                             and ele.parent.name not in ['meta', 'style', 'link']]

                translated_data = self.translate_tag(text_list)
                nextpos = -1

                for ele in epub_eles:
                    if isinstance(ele, element.NavigableString) and str(ele).strip() not in ['', 'html']:
                        nextpos += 1
                        if nextpos < len(translated_data):
                            original_text, translated_text = translated_data[nextpos]
                            # content = self.replace_translation_dict(translated_text[nextpos])
                            # print(f"{original_text} [Translated]: {translated_text}")
                            ele.replace_with(element.NavigableString(f"{original_text} [Translated]: {translated_text}"))

                # 将修改后的内容写回文件
                with open(xml_file, "w", encoding="utf-8") as w:
                    w.write(str(soup))

            # 随机等待时间
            time.sleep(random.uniform(3, 9))  # 随机等待3到9秒

        except Exception as e:
            print(f"An error occurred: {e}")


    def translate_tag(self, text_list):
        """将文本列表进行翻译，并返回翻译后的内容，保留翻译前后的字符串。"""

        combined_contents = self.combine_words(text_list)
        translated_contents = self.multithreads_translate(combined_contents)
        extracted_contents = self.extract_words(translated_contents)

        translation_pairs = []
        for orig, trans in zip(text_list, extracted_contents):
            # 将原始文本和翻译文本作为元组添加到列表中
            translation_pairs.append((orig, trans if trans else orig))  # 如果翻译失败，保留原始文本

        # print(f"origine text: {text_list}")
        # print(f"extracted_contents: {extracted_contents}")
        # print(f"translation_pairs: {translation_pairs}")
        return translation_pairs

    # def multithreads_translate(self, text_list):
    #     """使用多线程翻译文本列表，返回原始文本和翻译文本的元组。"""
    #     results = []
    #     pool = ThreadPool(4)
    #     try:
    #         results = pool.map(self.translate_text, text_list)
    #     except Exception as e:
    #         print(f'Translating text: [{pcolors.FAIL} FAIL {pcolors.ENDC}] - {e}')
    #         raise
    #     finally:
    #         pool.close()
    #         pool.join()
    #     return results
    def multithreads_html_translate(self):
        """使用多线程翻译 HTML 文件。"""
        pool = ThreadPool(4)
        try:
            # 使用 tqdm 库显示处理进度
            for _ in tqdm.tqdm(pool.imap_unordered(self.translate_html, self.html_list_path), total=len(self.html_list_path), desc='Translating'):
                pass
        except Exception as e:
            print(f'Translating epub: [{pcolors.FAIL} FAIL {pcolors.ENDC}] - {e}')
            raise
        finally:
            pool.close()
            pool.join()

    def multithreads_translate(self, text_list):
        """使用多进程翻译文本列表，返回原始文本和翻译文本的元组。"""
        results = []
        with Pool(processes=4) as pool:  # 替换为多进程
            try:
                results = pool.map(self.translate_text, text_list)
            except Exception as e:
                print(f'Translating text: [{pcolors.FAIL} FAIL {pcolors.ENDC}] - {e}')
                raise
        return results
    #
    # def multithreads_html_translate(self):
    #     """使用多进程翻译 HTML 文件。"""
    #     with Pool(processes=4) as pool:  # 替换为多进程
    #         try:
    #             # 使用 tqdm 库显示处理进度
    #             for _ in tqdm.tqdm(pool.imap_unordered(self.translate_html, self.html_list_path),
    #                                total=len(self.html_list_path), desc='Translating'):
    #                 pass
    #         except Exception as e:
    #             print(f'Translating epub: [{pcolors.FAIL} FAIL {pcolors.ENDC}] - {e}')
    #             raise

    def translate_text(self, text):
        """翻译单个文本，支持字符串和字符串列表。"""
        translator = google_translator(timeout=5, url_suffix="com.jp", proxies={'http': 'http://192.168.30.42:11110',
                                                                                'https': 'http://192.168.30.42:11110'})
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # 打印原始文本
                # print(f"Translating text: {text}")
                if isinstance(text, str):
                    result = translator.translate(text, self.dest_lang)
                    # print(f"Translated result: {result}")
                    return result
                else:
                    results = [translator.translate(substr, self.dest_lang) for substr in text]
                    # print(f"Translated results: {results}")
                    return results  # 返回翻译后的文本列表
            except Exception as e:
                print(f"Error during translation attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    wait_time = random.uniform(2, 7)
                    print(f"Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)

        print("Translation failed after multiple attempts. Returning original text.")
        return text  # 或者返回 None

    def extract_words(self, text_list):
        """从翻译后的文本中提取单独的文本块。"""
        extracted_text = []
        for text in text_list:
            extracted_text.extend(text.split('_____'))  # 使用 '_____' 进行分割
        filtered_list = [item for item in extracted_text if item.strip() != '']
        return filtered_list

    def zip_epub(self):
        """将翻译后的内容压缩为 EPUB 文件。"""
        print('Making the translated epub file...', end='\r')
        try:
            filename = f"{self.file_extracted_path}.epub"
            with open(Path(self.file_extracted_path) / 'mimetype', 'w') as file:
                file.write('application/epub+zip')
            with zipfile.ZipFile(filename, 'w') as archive:
                archive.write(Path(self.file_extracted_path) / 'mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
                for file in Path(self.file_extracted_path).rglob('*.*'):
                    archive.write(file, file.relative_to(Path(self.file_extracted_path)), compress_type=zipfile.ZIP_DEFLATED)

            shutil.rmtree(self.file_extracted_path)  # 删除解压的文件夹
            print(f'Making the translated epub file: [{pcolors.GREEN} DONE {pcolors.ENDC}]')
        except Exception as e:
            print(e)
            print(f'Making the translated epub file: [{pcolors.FAIL} FAIL {pcolors.ENDC}]')

    def start(self, file_path):
        """启动翻译过程。"""
        self.get_epub_file_info(file_path)
        if self.extract_epub():
            self.get_epub_html_path()
            self.multithreads_html_translate()
            self.zip_epub()


if __name__ == "__main__":

    # 创建一个ArgumentParser对象，并传入构造函数参数变量description
    parser = argparse.ArgumentParser(
        description='A tool for translating epub files to different languages using the Google Translate, with support for custom dictionaries.')

    # 添加可选参数"-v",-v 是参数的短形式，--version 是参数的长形式。当用户在命令行中使用 -v 或 --version 时，程序将执行 version 动作，显示 epub-translator v%s，其中 %s 将被 TOOL_VERSION 的值替换
    parser.add_argument('-v', '--version', action='version',
                        version='epub-translator v%s' % TOOL_VERSION)
    # 添加位置参数"epub_file_path"，用户需要提供一个 epub 文件的路径。程序将使用这个路径来找到要翻译的 epub 文件。type=str 指定了该参数的类型应为字符串
    parser.add_argument('epub_file_path', type=str,
                        help='path to the epub file')
    # 添加可选参数"-l"，用于指定目标语言。-l 是参数的短形式，--lang 是参数的长形式。metavar='dest_lang' 指定了在帮助信息中显示的参数值的名称
    parser.add_argument('-l', '--lang', type=str, metavar='dest_lang',
                        help='destination language')
    # 添加可选参数"-d"，用于指定翻译字典的路径。-d 是参数的短形式，--dict 是参数的长形式。metavar='dict_path' 指定了在帮助信息中显示的参数值的名称
    parser.add_argument('-d', '--dict', type=str, metavar='dict_path',
                        help='path to the translation dictionary')
    # 使用parse_args方法解析parser对象，生成Namespace对象，参数会变成它的属性
    args = parser.parse_args()

    engine = TranslatorEngine()

    # check_for_tool_updates()

    if args.lang and args.lang not in LANGUAGES.keys():
        print('Can not find destination language: ' + args.lang)
        sys.exit()
    elif args.lang:
        engine.dest_lang = args.lang

    if args.dict:
        translation_dict_file_path = args.dict.replace(
            '&', '').replace('\'', '').replace('\"', '').strip()
        engine.translation_dict_file_path = os.path.abspath(
            translation_dict_file_path)
        if not engine.get_translation_dict_contents():
            sys.exit()

    epub_file_path = args.epub_file_path.replace(
        '&', '').replace('\'', '').replace('\"', '').strip()
    epub_abs_file_path = os.path.abspath(epub_file_path)
    if os.path.isfile(epub_abs_file_path) and epub_abs_file_path.endswith('.epub'):
        engine.start(epub_abs_file_path)
    else:
        print('Epub file path is incorrect!')
        sys.exit()
