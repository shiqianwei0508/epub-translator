import argparse
import os
import re
import shutil
import sys
import zipfile
import time
import random
from multiprocessing.dummy import Pool as ThreadPool
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
        # 构造函数，初始化属性，目标翻译语言、文件路径、文件名称、文件解压路径、html列表路径、翻译字典、翻译字典文件路径、字典格式、最大翻译字数？
        self.dest_lang = 'zh-cn'
        self.file_path = ''
        self.file_name = ''
        self.file_extracted_path = ''
        self.html_list_path = []
        self.translation_dict = {}
        self.translation_dict_file_path = ''
        self.dict_format = '^[^:]+:[^:]+$'
        self.max_trans_words = 5000

    def get_epub_file_info(self, file_path):
        self.file_path = file_path
        self.file_name = os.path.splitext(os.path.basename(file_path))[0]
        # 在epub文件同级目录下，创建 "文件名_translated" 目录
        self.file_extracted_path = os.path.join(os.path.abspath(
            os.path.join(file_path, os.pardir)), self.file_name + '_translated')

    def extract_epub(self):
        try:
            with zipfile.ZipFile(self.file_path, 'r') as zip:
                print('Extracting the epub file...', end='\r')
                zip.extractall(self.file_extracted_path)
                print(
                    f'Extracting the epub file: [{pcolors.GREEN} DONE {pcolors.ENDC}]')
            return True
        except Exception:
            print(
                f'Extracting the epub file: [{pcolors.FAIL} FAIL {pcolors.ENDC}]')
            return False

    def get_epub_html_path(self):
        for file_type in ['*.[hH][tT][mM][lL]', '*.[xX][hH][tT][mM][lL]', '*.[hH][tT][mM]']:

            # 查找 self.file_extracted_path 路径下所有类型为 file_type 的文件，并将这些文件的绝对路径添加到 self.html_list_path 列表中
            # rglob 是 Python pathlib 模块中 Path 类的一个方法。这个方法会生成当前路径下所有满足指定模式的文件和目录的路径，包括当前路径的所有子目录。这个方法的名称 rglob 是 "recursive glob" 的缩写，表示它是一个递归的全局搜索方法
            self.html_list_path += [str(p.resolve())
                                    for p in list(Path(self.file_extracted_path).rglob(file_type))]

    def multithreads_html_translate(self):
        pool = ThreadPool(8)
        try:
            # 使用了 tqdm 库来显示处理进度。pool.imap_unordered(self.translate_html, self.html_list_path) 是一个迭代器，它会并行地对 self.html_list_path 列表中的每个元素调用 self.translate_html 函数。tqdm.tqdm() 函数会显示一个进度条，total=len(self.html_list_path) 设置了进度条的总长度，desc='Translating' 设置了进度条的描述
            for _ in tqdm.tqdm(pool.imap_unordered(self.translate_html, self.html_list_path), total=len(self.html_list_path), desc='Translating'):
                pass
        except Exception:
            print(f'Translating epub: [{pcolors.FAIL} FAIL {pcolors.ENDC}]')
            raise
        pool.close()
        pool.join()

    def translate_html(self, html_file):
        # 打开了一个 HTML 文件，并将文件内容读入一个文件对象 f
        with open(html_file, encoding='utf-8') as f:
            # 使用 BeautifulSoup 库解析了文件内容。'xml' 参数指定了解析器类型
            soup = BeautifulSoup(f, 'xml')
            # 提取所有的子元素，并将它们存入了一个列表 epub_eles
            epub_eles = list(soup.descendants)

            text_list = []
            for ele in epub_eles:
                # 判断当前元素是否是一个文本元素，并且这个元素的文本内容不是空字符串或者 'html'
                if isinstance(ele, element.NavigableString) and str(ele).strip() not in ['', 'html']:
                    # 将当前元素的文本内容添加到 text_list 中
                    text_list.append(str(ele))

            translated_text = self.translate_tag(text_list)
            nextpos = -1

            for ele in epub_eles:
                if isinstance(ele, element.NavigableString) and str(ele).strip() not in ['', 'html']:
                    nextpos += 1
                    if nextpos < len(translated_text):
                        content = self.replace_translation_dict(
                            translated_text[nextpos])
                        ele.replace_with(element.NavigableString(content))

            with open(html_file, "w", encoding="utf-8") as w:
                w.write(str(soup))
            w.close()
        f.close()

    def replace_translation_dict(self, text):
        if self.translation_dict:
            for replace_text in self.translation_dict.keys():
                if replace_text in text:
                    text = text.replace(
                        replace_text, self.translation_dict[replace_text])
        return text

    def get_translation_dict_contents(self):
        if os.path.isfile(self.translation_dict_file_path) and self.translation_dict_file_path.endswith('.txt'):
            print('Translation dictionary detected.')
            with open(self.translation_dict_file_path, encoding='utf-8') as f:
                for line in f.readlines():
                    if re.match(self.dict_format, line):
                        split = line.rstrip().split(':')
                        self.translation_dict[split[0]] = split[1]
                    else:
                        print(
                            f'Translation dictionary is not in correct format: {line}')
                        return False
            f.close()
        else:
            print('Translation dictionary file path is incorrect!')
            return False
        return True

    def translate_tag(self, text_list):
        combined_contents = self.combine_words(text_list)
        translated_contents = self.multithreads_translate(combined_contents)
        extracted_contents = self.extract_words(translated_contents)

        return extracted_contents

    def translate_text(self, text):
        translator = google_translator(timeout=5)
        if type(text) is not str:
            translate_text = ''
            for substr in text:
                translate_substr = translator.translate(substr, self.dest_lang)
                translate_text += translate_substr
        else:
            translate_text = translator.translate(text, self.dest_lang)
            #time.sleep(random.uniform(1,3))
        return translate_text

    def multithreads_translate(self, text_list):
        results = []
        pool = ThreadPool(8)
        try:
            results = pool.map(self.translate_text, text_list)
        except Exception:
            print(f'Translating epub: [{pcolors.FAIL} FAIL {pcolors.ENDC}]')
            raise
        pool.close()
        pool.join()
        return results

    def combine_words(self, text_list):
        combined_text = []
        combined_single = ''
        for text in text_list:
            combined_single_prev = combined_single
            if combined_single:
                combined_single += '\n-----\n' + text
            else:
                combined_single = text
            if len(combined_single) >= self.max_trans_words:
                combined_text.append(combined_single_prev)
                combined_single = '\n-----\n' + text
        combined_text.append(combined_single)
        return combined_text

    def extract_words(self, text_list):
        extracted_text = []
        for text in text_list:
            extract = text.split('-----')
            extracted_text += extract
        return extracted_text

    def zip_epub(self):
        print('Making the translated epub file...', end='\r')
        try:
            # zipf = zipfile.ZipFile(
            #     self.file_extracted_path + '.epub', 'w', zipfile.ZIP_DEFLATED)
            # self.zipdir(self.file_extracted_path, zipf)
            # zipf.writestr("mimetype", "application/epub+zip")
            # zipf.close()

            filename = f"{self.file_extracted_path}.epub"
            file_extracted_absolute_path = Path(self.file_extracted_path)

            with open(str(file_extracted_absolute_path / 'mimetype'), 'w') as file:
                file.write('application/epub+zip')
            with zipfile.ZipFile(filename, 'w') as archive:
                archive.write(
                    str(file_extracted_absolute_path / 'mimetype'), 'mimetype',
                    compress_type=zipfile.ZIP_STORED)
                for file in file_extracted_absolute_path.rglob('*.*'):
                    archive.write(
                        str(file), str(file.relative_to(
                            file_extracted_absolute_path)),
                        compress_type=zipfile.ZIP_DEFLATED)

            shutil.rmtree(self.file_extracted_path)
            print(
                f'Making the translated epub file: [{pcolors.GREEN} DONE {pcolors.ENDC}]')
        except Exception as e:
            print(e)
            print(
                f'Making the translated epub file: [{pcolors.FAIL} FAIL {pcolors.ENDC}]')

    def zipdir(self, path, ziph):
        for root, dirs, files in os.walk(path):
            for file in files:
                ziph.write(os.path.join(root, file),
                           os.path.relpath(os.path.join(root, file),
                                           os.path.join(path, self.file_name + '_translated')))

    def start(self, file_path):
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
