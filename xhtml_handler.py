import random
import time
import tqdm
from bs4 import BeautifulSoup
from bs4 import element
from multiprocessing.dummy import Pool as ThreadPool
from .pcolors import pcolors

class XHTMLHandler:
    def __init__(self, xhtml_list_path, translator):
        self.xhtml_list_path = xhtml_list_path
        self.translator = translator

    def translate_html_files(self):
        pool = ThreadPool(4)
        try:
            for _ in tqdm.tqdm(pool.imap_unordered(self.translate_html, self.xhtml_list_path), total=len(self.xhtml_list_path), desc='Translating'):
                pass
        except Exception as e:
            print(f'Translating epub: [{pcolors.FAIL} FAIL {pcolors.ENDC}] - {e}')
            raise
        finally:
            pool.close()
            pool.join()

    def translate_html(self, xml_file):
        try:
            with open(xml_file, encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'lxml-xml')
                epub_eles = list(soup.descendants)
                text_list = [str(ele) for ele in epub_eles if isinstance(ele, element.NavigableString) and str(ele).strip() not in ['', 'html'] and ele.parent.name not in ['meta', 'style', 'link', 'code', 'li']]
                translated_data = self.translator.translate_list(text_list)
                nextpos = -1

                for ele in epub_eles:
                    if isinstance(ele, element.NavigableString) and str(ele).strip() not in ['', 'html']:
                        nextpos += 1
                        if nextpos < len(translated_data):
                            original_text, translated_text = translated_data[nextpos]
                            ele.replace_with(element.NavigableString(f"{original_text}  {translated_text}"))

            with open(xml_file, "w", encoding="utf-8") as w:
                w.write(str(soup))
            time.sleep(random.uniform(3, 5))

        except Exception as e:
            print(f"An error occurred: {e}")