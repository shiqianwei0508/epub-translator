import re


def contains_language(text_to_check, lang_code):
    """
    检查文本中是否包含指定语言的字符。

    :param text_to_check: 要检测的文本
    :param lang_code: 目标语言的代码，例如 'en', 'zh', 'zh-cn', 'es', 'fr', 'de', 'it', 'ru', 'ja', 'ko'
    :return: 如果文本中包含指定语言的字符，返回 True；否则返回 False
    """

    language_patterns = {
        'zh': r'[\u4e00-\u9fff]',  # 中文
        'zh-cn': r'[\u4e00-\u9fff]',  # 简体中文
        'en': r'[a-zA-Z]',  # 英文
        'es': r'[a-zA-ZñÑ]',  # 西班牙文
        'fr': r'[a-zA-Zàâçéèêëîïôûùÿ]',  # 法文
        'de': r'[a-zA-ZäöüßÄÖÜ]',  # 德文
        'it': r'[a-zA-Zàèéìòù]',  # 意大利文
        'ru': r'[\u0400-\u04FF]',  # 俄文
        'ja': r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]',  # 日文
        'ko': r'[\uAC00-\uD7A3]'  # 韩文
    }

    # 获取目标语言的正则表达式
    pattern = language_patterns.get(lang_code)

    if pattern is None:
        raise ValueError("Unsupported language code: {}".format(lang_code))

    return bool(re.search(pattern, text_to_check))


if __name__ == '__main__':
    # 示例用法
    text = "Hello, how are you? 我是谁！ ¿Dónde está el baño?  Привет! こんにちは 안녕하세요"

    # 测试不同语言的检测
    print(contains_language(text, 'zh'))  # 输出: True
    print(contains_language(text, 'zh-cn'))  # 输出: True
    print(contains_language(text, 'en'))  # 输出: True
    print(contains_language(text, 'es'))  # 输出: True
    print(contains_language(text, 'fr'))  # 输出: False
    print(contains_language(text, 'de'))  # 输出: False
    print(contains_language(text, 'it'))  # 输出: False
    print(contains_language(text, 'ru'))  # 输出: True
    print(contains_language(text, 'ja'))  # 输出: True
    print(contains_language(text, 'ko'))  # 输出: True
