import re

from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException   # 为了确保每次检测的一致性

DetectorFactory.seed = 0 


def detect_language(text):
    try:   # 检测语言
        language = detect(text)
        return language
    except LangDetectException:
        return "无法检测语言"


def contains_chinese(text):
    # 正则表达式匹配中文字符
    pattern = re.compile(r'[\u4e00-\u9fff]')
    return bool(pattern.search(text))


# 示例用法
if __name__ == "__main__":
    text = "This is a girl"
    language = detect_language(text)
    print(f"检测到的语言: {language}")
    print(type(language))
