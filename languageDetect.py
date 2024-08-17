from langdetect import detect, DetectorFactory from langdetect.lang_detect_exception import LangDetectException # 为了确保每次检测的一致性 

DetectorFactory.seed = 0 

def detect_language(text): 
try: # 检测语言 
    language = detect(text) 
    return language 
except LangDetectException: 
    return "无法检测语言" 

# 示例用法 
text = "Bonjour, comment ça va?" 
language = detect_language(text) 
print(f"检测到的语言: {language}")