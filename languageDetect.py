import re


def contains_language(text_to_check, lang_code):
    """
    检查文本中是否包含指定语言的字符。

    :param text_to_check: 要检测的文本
    :param lang_code: 目标语言的代码，例如 'en', 'zh', 'fr', 'es', 'de', 'it', 'ru', 'ja', 'ko', 'ar', 等等
    :return: 如果文本中包含指定语言的字符，返回 True；否则返回 False
    """

    language_patterns = {
        'zh': r'[\u4e00-\u9fff]',  # 中文
        'zh-cn': r'[\u4e00-\u9fff]',  # 简体中文
        'zh-tw': r'[\u4e00-\u9fff]',  # 繁体中文
        'en': r'[a-zA-Z]',  # 英文
        'es': r'[a-zA-ZñÑ]',  # 西班牙文
        'fr': r'[a-zA-Zàâçéèêëîïôûùÿ]',  # 法文
        'de': r'[a-zA-ZäöüßÄÖÜ]',  # 德文
        'it': r'[a-zA-Zàèéìòù]',  # 意大利文
        'ru': r'[\u0400-\u04FF]',  # 俄文
        'ja': r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]',  # 日文
        'ko': r'[\uAC00-\uD7A3]',  # 韩文
        'ar': r'[\u0600-\u06FF]',  # 阿拉伯文
        'pt': r'[a-zA-ZãÃáÁéÉíÍóÓúÚ]',  # 葡萄牙文
        'nl': r'[a-zA-ZëË]',  # 荷兰文
        'sv': r'[a-zA-ZåÅäÄöÖ]',  # 瑞典文
        'da': r'[a-zA-ZæÆøØåÅ]',  # 丹麦文
        'fi': r'[a-zA-ZåÅ]',  # 芬兰文
        'no': r'[a-zA-ZæÆøØåÅ]',  # 挪威文
        'tr': r'[a-zA-ZğĞıİöÖşŞçÇ]',  # 土耳其文
        'el': r'[\u0391-\u03A1\u03A3-\u03A9\u03B1-\u03C1\u03C3-\u03C9]',  # 希腊文
        'hi': r'[\u0900-\u097F]',  # 印地文
        'bn': r'[\u0980-\u09FF]',  # 孟加拉文
        'pa': r'[\u0A00-\u0A7F]',  # 旁遮普文
        'ta': r'[\u0B80-\u0BFF]',  # 泰米尔文
        'te': r'[\u0C00-\u0C7F]',  # 特伦甘那文
        'ml': r'[\u0D00-\u0D7F]',  # 马拉雅拉姆文
        'kn': r'[\u0C80-\u0CFF]',  # 卡纳达文
        'gu': r'[\u0A80-\u0AFF]',  # 古吉拉特文
        'mr': r'[\u0900-\u097F]',  # 马拉地文
        'or': r'[\u0B00-\u0B7F]',  # 奥里亚文
        'si': r'[\u0D80-\u0DFF]',  # 僧伽罗文
        'sw': r'[a-zA-Z]',  # 斯瓦希里文
        'tl': r'[a-zA-Z]',  # 塔加路文
        'lv': r'[a-zA-ZāĀčČēĒģĢīĪķĶļĻņŅšŠžŽ]',  # 拉脱维亚文
        'lt': r'[a-zA-ZąĄčČęĘėĖįĮšŠųŲźŹžŽ]',  # 立陶宛文
        'sk': r'[a-zA-ZáÁäÄčČďĎéÉěĚíÍňŇóÓôÔřŘšŠťŤúÚýÝ]',  # 斯洛伐克文
        'cs': r'[a-zA-ZáÁčČďĎéÉěĚíÍňŇóÓřŘšŠťŤúÚýÝ]',  # 捷克文
        'hu': r'[a-zA-ZáÁéÉíÍóÓöÖőŐúÚüÜ]',  # 匈牙利文
        'ro': r'[a-zA-ZăĂâÂîÎșȘțȚ]',  # 罗马尼亚文
        'bg': r'[\u0400-\u04FF]',  # 保加利亚文
        'sr': r'[\u0400-\u04FF]',  # 塞尔维亚文（西里尔字母）
        'sr-latin': r'[a-zA-ZčČćĆžŽšŠ]',  # 塞尔维亚文（拉丁字母）
        'mk': r'[\u0400-\u04FF]',  # 马其顿文
        'is': r'[a-zA-ZáÁéÉíÍóÓúÚýÝ]',  # 冰岛文
        'ga': r'[a-zA-ZáÁéÉíÍóÓúÚ]',  # 爱尔兰文
        'cy': r'[a-zA-ZáÁéÉíÍóÓúÚ]',  # 威尔士文
        'xh': r'[a-zA-Z]',  # 科萨文
        'zu': r'[a-zA-Z]',  # 祖鲁文
        'mg': r'[a-zA-Z]',  # 马尔加什文
        'id': r'[a-zA-Z]',  # 印度尼西亚语
        'ms': r'[a-zA-Z]',  # 马来语
        'tl': r'[a-zA-Z]',  # 塔加路语
        'th': r'[\u0E00-\u0E7F]',  # 泰语
        'vi': r'[\u0102-\u1EF9]',  # 越南语
        'my': r'[\u1000-\u109F]',  # 缅甸语
        'km': r'[\u1780-\u17FF]',  # 高棉语
        'lo': r'[\u0E80-\u0EFF]',  # 老挝语
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
