import ebooklib
from ebooklib import epub
from xhtmlTranslate import Logger

import warnings
# 忽略特定警告
warnings.filterwarnings("ignore", category=UserWarning, module='ebooklib')
warnings.filterwarnings("ignore", category=FutureWarning, module='ebooklib')



logger = Logger(log_file='app01.log')

epub_path='Python编程与初级数学.epub'

book = epub.read_epub(epub_path)
# print(book.title)
# print(book.get_metadata('DC', 'title'))
# print(book.get_metadata('DC', 'description'))
# print(book.get_metadata('DC', 'publisher'))
# print(book.get_metadata('DC', 'language'))
# print(book.get_metadata('DC', 'copyright'))
# print(book.get_metadata('DC', 'identifier'))
# print(book.get_metadata('DC', 'creator'))




# 获取所有项目
# # items = book.get_items()
items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
logger.debug(f"Items found in the book: {[item.get_id() for item in items]}")




# for item in book.get_items():
#     if item.get_type() == ebooklib.ITEM_DOCUMENT:
#         print('==================================')
#         print('NAME : ', item.get_name())
#         print('----------------------------------')
#         print(item.get_body_content())
#         print('==================================')

# chapters = []
# # 遍历所有项目，寻找EpubHtml类型的章节
# for item in items:
#     if isinstance(item, epub.EpubHtml):
#         chapters.append(item)
#         logger.debug(f"Found chapter: {item.get_id()} - Title: {item.get_title()}")
# logger.debug(f"Extracted {len(chapters)} chapters from: {epub_path}")




chapters = []
for item in book.get_items():
    if item.get_type() == ebooklib.ITEM_DOCUMENT:
        chapters.append(item)
        logger.debug(f"Found chapter: {item.get_id()} - Name: {item.get_name()}")

logger.debug(f"Extracted {len(chapters)} chapters from: {epub_path}")

print(chapters[0].get_content())
# print(chapters[0].get_content_str())

