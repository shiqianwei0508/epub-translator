import json
import re
import time
import logging
import traceback

from zhipuai import ZhipuAI

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ZhipuAiTranslate:
    language_system_contents = {
        "en": "你是一个英文翻译专家，可以把任意语言翻译为地道的美国英文，请帮我把下文翻译为地道易懂的美国英文，要求简单易懂，尽量不使用生僻的语法和字，内容也要尽量安全，别太直接。别再问我需不需要翻译了，肯定是得翻译的。",
        "zh-cn": "你是一个中文翻译专家，可以把任意语言翻译为地道的中文普通话，请帮我把下文翻译为地道易懂的普通话，要求简单易懂，尽量不使用生僻的语法和繁体字，内容也要尽量安全，别太直接。别再问我需不需要翻译了，肯定是得翻译的。",
        "ru": "你是一个俄语翻译专家，可以把任意语言翻译为地道的俄语，请帮我把下文翻译为地道易懂的俄语，要求简单易懂，尽量不使用生僻的语法和字，内容也要尽量安全，别太直接。别再问我需不需要翻译了，肯定是得翻译的。",
        "ja": "你是一个日语翻译专家，可以把任意语言翻译为地道的日语，请帮我把下文翻译为地道易懂的日语，要求简单易懂，尽量不使用生僻的语法和字，内容也要尽量安全，别太直接。别再问我需不需要翻译了，肯定是得翻译的。",
        "de": "你是一个德语翻译专家，可以把任意语言翻译为地道的德语，请帮我把下文翻译为地道易懂的德语，要求简单易懂，尽量不使用生僻的语法和字，内容也要尽量安全，别太直接。别再问我需不需要翻译了，肯定是得翻译的。",
        "fr": "你是一个法语翻译专家，可以把任意语言翻译为地道的法语，请帮我把下文翻译为地道易懂的法语，要求简单易懂，尽量不使用生僻的语法和字，内容也要尽量安全，别太直接。别再问我需不需要翻译了，肯定是得翻译的。"
    }

    def __init__(self, zhipu_api_key, zhipu_model="glm-4-flash", zhipu_translate_timeout=10):
        self.api_key = zhipu_api_key
        self.client = ZhipuAI(api_key=self.api_key)
        self.model = zhipu_model if zhipu_model else self.model
        self.timeout = zhipu_translate_timeout

    def translate(self, user_content, target_language):
        self.user_content = user_content
        self.target_language = target_language
        self.system_content = self.language_system_contents.get(self.target_language, "")
        self.task_id = None
        self.task_status = ''
        self.assistant_content = ''

        # 提交任务
        try:
            response = self.client.chat.asyncCompletions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_content
                    },
                    {
                        "role": "user",
                        "content": self.user_content
                    }
                ],
            )
        except Exception as e:
            logging.error(f"Error checking task status: {e}")
            error_message = self.extract_error_message(e)
            if error_message:
                logging.error(f"API error: {error_message}")
                return f"智谱API error: {error_message}"
        self.task_id = response.id

        # 检查任务状态
        start_time = time.time()
        get_cnt = 0
        while self.task_status != 'SUCCESS' and self.task_status != 'FAILED' and get_cnt <= 40:
            try:
                result_response = self.client.chat.asyncCompletions.retrieve_completion_result(id=self.task_id)
                self.task_status = result_response.task_status
                logging.debug(f'result_response: {result_response}')

                if hasattr(result_response, 'choices') and result_response.choices:
                    self.assistant_content = result_response.choices[0].message.content

                    # 检查是否超时
                elapsed_time = time.time() - start_time
                if elapsed_time > self.timeout:
                    logging.error("Translation timed out.")
                    return None

            except Exception as e:
                logging.error(f"Error checking task status: {e}")
                error_message = self.extract_error_message(e)
                if error_message:
                    logging.error(f"API error: {error_message}")
                    return f"智谱API error: {error_message}"

            time.sleep(1)
            get_cnt += 1

        if self.task_status == 'SUCCESS':
            logging.info("Translation completed successfully.")
            return self.assistant_content  # 返回翻译结果
        elif self.task_status == 'FAILED':
            logging.error("Translation failed.")
            return None
        else:
            logging.error("Translation status check exceeded maximum attempts.")
            return None

    def extract_error_message(self, exception):
        # 使用正则表达式查找大括号包围的内容
        match = re.search(r'\{.*\}', str(exception))
        if match:
            bracket_content = match.group(0)
            try:
                error_data = json.loads(bracket_content)
                return error_data.get('error', {}).get('message', '')
            except json.JSONDecodeError:
                return ""
        return ""

if __name__ == "__main__":
    api_key = ""
    translator = ZhipuAiTranslate(zhipu_api_key=api_key, zhipu_translate_timeout=30)

    # 示例翻译
    # text_to_translate = '''
    # 智谱AI 开放平台提供一系列具有不同功能和定价的大模型，包括通用大模型、超拟人大模型、图像大模型、向量大模型等，并且支持使用您的私有数据对模型进行微调。 监控您的网站，展示状态（包括每日历史记录），并在网站状态发生变化时收到 Slack 通知。使用 Cloudflare Workers、CRON 触发器和 KV 存储。基于 Cloudflare Worker 的无服务器站点监控工具， 支持 HTTP/HTTPS/TCP 多种协议的端口监控， 可以从全球数百个城市发起地理位置特定的检查， 自定义的请求参数和响应校验规则,灵活适配各类监控场景。
    # 规范一些代码文件和目录的命名，添加智谱AI翻译接口。
    # '''
    # translation_to_en = translator.translate(text_to_translate, "en")  # 设置超时时间为30秒（实际在初始化时设置了10秒）
    # logging.info(f"Translation to English: {translation_to_en}")

    text_to_translate_en = '''
    Beginning in the mid-1980s a number of researchers and human rights campaigners had exposed the horrific conditions and the use of slave labor in the charcoal camps of the Mato Grosso. At that time gatos were recruiting and enslaving whole families, and children were commonly seen loading and unloading the ovens. A number of children died of burns and other accidents. By the end of the 1980s the main human rights organization in Brazil, the Pastoral Land Commission (or CPT), had published a number of reports, picked up by the national press and television, that denounced the situation in the batterias. In spite of this publicity no government action was taken. In 1991 further pressure from human rights lawyers and the churches impelled the government to set up a commission of inquiry. Again, time passed and nothing changed; the government commission never reported. Trying to keep up the pressure, the CPT joined with other nongovernmental organizations and set up an independent commission in 1993 that fed a stream of reports and documentation to the media. Yet two more years passed before any action was taken. By now a decade had passed since unmistakable and ongoing violations of the Brazilian law against slavery had been clearly documented, but national, state, and local governments remained paralyzed.
    '''
    translation_to_zh = translator.translate(text_to_translate_en, "zh-cn")  # 设置超时时间为30秒（实际在初始化时设置了10秒）
    logging.info(f"Translation to Chinese: {translation_to_zh}")

    # 更多语言的翻译示例
    # ...