import random
import time
from multiprocessing.pool import ThreadPool
from google_trans_new import google_translator
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
class TextCombiner:
    def __init__(self, max_trans_words):
        self.max_trans_words = max_trans_words
        self.dest_lang = 'zh-cn'  # 目标翻译语言
        self.file_path = ''  # EPUB 文件路径
        self.file_name = ''  # EPUB 文件名称
        self.file_extracted_path = ''  # EPUB 解压路径
        self.html_list_path = []  # HTML 文件路径列表
        self.translation_dict = {}  # 翻译字典
        self.translation_dict_file_path = ''  # 翻译字典文件路径
        self.dict_format = '^[^:]+:[^:]+$'  # 翻译字典格式

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

    def multithreads_translate(self, text_list):
        """使用多线程翻译文本列表，返回原始文本和翻译文本的元组。"""
        results = []
        pool = ThreadPool(8)
        try:
            results = pool.map(self.translate_text, text_list)
        except Exception as e:
            print(f'Translating text: [{pcolors.FAIL} FAIL {pcolors.ENDC}] - {e}')
            raise
        finally:
            pool.close()
            pool.join()
        return results
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
                    wait_time = random.uniform(3, 5)
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

# 示例使用
text_list = [
    'On China', 'Table of Contents', 'Title Page', 'Copyright Page',
    'Dedication', 'Preface', 'CHAPTER 1 - The Singularity of China',
    'CHAPTER 2 - The Kowtow Question and the Opium War',
    'CHAPTER 3 - From Preeminence to Decline',
    'CHAPTER 4 - Mao’s Continuous Revolution',
    'CHAPTER 5 - Triangular Diplomacy and the Korean War',
    'CHAPTER 6 - China Confronts Both Superpowers',
    'CHAPTER 7 - A Decade of Crises',
    'CHAPTER 8 - The Road to Reconciliation',
    'CHAPTER 9 - Resumption of Relations: First Encounters with Mao and Zhou',
    'CHAPTER 10 - The Quasi-Alliance: Conversations with Mao',
    'CHAPTER 11 - The End of the Mao Era',
    'CHAPTER 12 - The Indestructible Deng',
    'CHAPTER 13 - “Touching the Tiger’s Buttocks” The Third Vietnam War',
    'CHAPTER 14 - Reagan and the Advent of Normalcy',
    'CHAPTER 15 - Tiananmen',
    'CHAPTER 16 - What Kind of Reform? Deng’s Southern Tour',
    'CHAPTER 17 - A Roller Coaster Ride Toward Another Reconciliation',
    'CHAPTER 18 - The New Millennium',
    'EPILOGUE', 'Notes', 'Index'
]

combiner = TextCombiner(max_trans_words=100)  # 设置一个最大翻译字数
result = combiner.combine_words(text_list)
translated_result = combiner.multithreads_translate(result)
extracted_contents = combiner.extract_words(translated_result)

translation_pairs = []
for orig, trans in zip(text_list, extracted_contents):
    # 将原始文本和翻译文本作为元组添加到列表中
    translation_pairs.append((orig, trans if trans else orig))  # 如果翻译失败，保留原始文本



# 打印结果
# for idx, block in enumerate(result):
#     print(f"Block {idx + 1}:\n{block}\n")
# print(result)
print(f"origine text: {text_list}")
# print(f"To Translate results: {result}")
# print(f"translated_result: {translated_result}")
print(f"extracted_contents: {extracted_contents}")
print(f"translation_pairs: {translation_pairs}")
