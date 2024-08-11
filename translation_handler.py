import os
import random
import time
from multiprocessing import Pool
from google_trans_new import google_translator

class TranslationHandler:
    def __init__(self, dest_lang, http_proxy='http://10.99.99.108:11110', transapi_suffix='com'):
        self.dest_lang = dest_lang
        self.translation_dict = {}
        self.max_trans_words = 5000
        self.min_trans_words = 2000
        self.http_proxy = http_proxy
        self.transapi_suffix = transapi_suffix

    def set_dictionary(self, file_path):
        self.translation_dict_file_path = file_path
        if not self.load_translation_dict():
            raise ValueError("Invalid translation dictionary.")

    def load_translation_dict(self):
        if os.path.isfile(self.translation_dict_file_path) and self.translation_dict_file_path.endswith('.txt'):
            print('Translation dictionary detected.')
            with open(self.translation_dict_file_path, encoding='utf-8') as f:
                for line in f.readlines():
                    if re.match(r'^[^:]+:[^:]+$', line):
                        split = line.rstrip().split(':')
                        self.translation_dict[split[0]] = split[1]
                    else:
                        print(f'Translation dictionary is not in correct format: {line}')
                        return False
        else:
            print('Translation dictionary file path is incorrect!')
            return False
        return True

    def translate_text(self, text):
        translator = google_translator(timeout=5, url_suffix=self.transapi_suffix, proxies={'http': self.http_proxy, 'https': self.http_proxy})
        max_retries = 5
        for attempt in range(max_retries):
            try:
                if isinstance(text, str):
                    return translator.translate(text, self.dest_lang)
                else:
                    return [translator.translate(substr, self.dest_lang) for substr in text]
            except Exception as e:
                print(f"Error during translation attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(2, 7))
        return text

    def translate_list(self, text_list):
        combined_contents = self.combine_words(text_list)
        translated_contents = self.multithreads_translate(combined_contents)
        extracted_contents = self.extract_words(translated_contents)
        return [(orig, trans if trans else orig) for orig, trans in zip(text_list, extracted_contents)]

    def combine_words(self, text_list):
        combined_text = []
        combined_single = ''
        for text in text_list:
            combined_single += text + '  _____  '
            if len(combined_single) >= random.randint(self.min_trans_words, self.max_trans_words):
                combined_text.append(combined_single)
                combined_single = ''
        if combined_single:
            combined_text.append(combined_single)
        return combined_text

    def multithreads_translate(self, text_list):
        results = []
        with Pool(processes=4) as pool:
            results = pool.map(self.translate_text, text_list)
        return results

    def extract_words(self, text_list):
        extracted_text = []
        for text in text_list:
            extracted_text.extend(text.split('_____'))
        return [item for item in extracted_text if item.strip() != '']