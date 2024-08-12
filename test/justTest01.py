import random
import re
import time
from itertools import cycle
import logging
from bs4 import BeautifulSoup, NavigableString
from google_trans_new import google_translator

from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

http_proxy = "http://192.168.30.42:11110"
transapi_suffixes = "com,com.tw,co.jp,com.hk".split(',')
dest_lang = "zh-cn"
transMode = 2
TranslateThreadWorkers = 16

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

with open('translation.xhtml', 'r', encoding='utf-8') as f:
    xhtml_content = f.read()



def format_result(original, translated):
    """根据模式格式化翻译结果。"""
    if transMode == 1:
        return translated  # 仅返回翻译文本
    elif transMode == 2:
        return f"{original} [{translated}]"  # 返回格式化的字符串
    else:
        raise ValueError("翻译模式错误")  # 抛出翻译模式错误

def translate_text(text):
    """翻译单个文本，支持字符串和字符串列表。"""
    max_retries = 8
    transapi_suffixes_cycle = cycle(transapi_suffixes)  # 使用无限循环

    current_suffix = next(transapi_suffixes_cycle)
    logger.debug(f"Using initial suffix: {current_suffix}")

    # 每次请求时都创建新的翻译器实例
    translator = google_translator(timeout=5, url_suffix=current_suffix,
                                   proxies={'http': http_proxy, 'https': http_proxy})

    for attempt in range(max_retries):
        try:
            logger.debug(f"Translating text: '{text}' using suffix: {current_suffix}")

            if isinstance(text, str):
                result = translator.translate(text, dest_lang)
                logger.debug(f"Translated result: '{result}'")
                return format_result(text, result)
            else:
                results = [translator.translate(substr, dest_lang) for substr in text]
                logger.debug(f"Translated results: {results}")
                return [format_result(substr, result) for substr, result in zip(text, results)]
        except Exception as e:
            logger.warning(f"Error during translation attempt {attempt + 1}: {e}")
            wait_time = random.uniform(2, 7)
            if attempt < 2:
                logger.warning(f"Retrying in {wait_time:.2f} seconds without changing suffix...")
            else:
                current_suffix = next(transapi_suffixes_cycle)
                translator = google_translator(timeout=5, url_suffix=current_suffix,
                                               proxies={'http': http_proxy, 'https': http_proxy})
                logger.warning(f"Retrying in {wait_time:.2f} seconds with new suffix: {current_suffix}...")

            time.sleep(wait_time)

    logger.error("Translation failed after multiple attempts. Returning original text.")
    return {"original": text, "error": "Translation failed"}


def translate_paragraphs(xhtml_content):
    soup = BeautifulSoup(xhtml_content, 'html.parser')
    logger.debug("Starting translation of paragraphs.")

    # 支持翻译的标签
    supported_tags = ["p", "title", "h1", "h2"]
    translations = []  # 存储待替换的文本与翻译结果

    # 将 soup.descendants 转换为列表，以避免在遍历过程中修改结构
    descendants = list(soup.descendants)

    # 收集需要翻译的文本和对应的元素
    texts_to_translate = []
    for element in descendants:
        if isinstance(element, NavigableString) and element.strip() and element.parent.name in supported_tags:
            # 检查元素是否包含字母且不只是数字
            if re.search(r'[a-zA-Z]', element) and not re.match(r'^\d+$', element):
                need_translate = element.strip()
                texts_to_translate.append((element, need_translate))  # 存储原始元素和文本
    logger.debug(f"texts_to_translate: {texts_to_translate}")

    # 使用 ThreadPoolExecutor 进行并发翻译
    with ThreadPoolExecutor(max_workers=TranslateThreadWorkers) as executor:
        # 使用 tqdm 显示进度条
        future_to_text = {executor.submit(translate_text, text): (element, text) for element, text in
                          texts_to_translate}

        for future in tqdm(as_completed(future_to_text), total=len(future_to_text), desc="Translating a chapter"):
            element, original_text = future_to_text[future]
            # time.sleep(random.uniform(0.1, 1))  # 随机等待时间，0.1到1秒
            try:
                translated_text = future.result()
                if isinstance(translated_text, dict) and "error" in translated_text:
                    logger.error(f"Failed to translate '{original_text}': {translated_text['error']}")
                    continue

                translations.append((element, translated_text))  # 存储原始元素和翻译结果
            except Exception as e:
                logger.error(f"Translation error for text '{original_text}': {str(e)}")

    # 统一替换翻译结果
    for element, translated_text in translations:
        element.replace_with(translated_text)
        logger.debug(f"Replaced with translated text: '{translated_text}'")

    logger.debug("Finished translation of paragraphs.")
    return str(soup)

def check_xhtml(xhtml_content):
    soup = BeautifulSoup(xhtml_content, 'html.parser')
    logger.debug("Checking XHTML content.")

    for p in soup.find_all('p'):
        for element in p.descendants:  # 遍历所有子孙节点
            if isinstance(element, NavigableString) and element.strip():
                logger.debug(f"Found text in paragraph: '{element.strip()}'")

    logger.debug("Finished checking XHTML content.")



# Start time counter
start_time = time.time()

translated_xhtml = translate_paragraphs(xhtml_content)

output_file_path = "translation_translated.html"
with open(output_file_path, 'w', encoding='utf-8') as file:
    file.write(translated_xhtml)

# check_xhtml(xhtml_content)
# End time counter
end_time = time.time()
execution_time = end_time - start_time  # Calculate execution time

logging.info(f"Translation completed. Output saved to: {output_file_path}")
logging.info(f"Execution time: {execution_time:.2f} seconds")