import time
import logging
from zhipuai import ZhipuAI

# 配置日志记录
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class ZhipuAiTranslate:
    language_system_contents = {
        "en": "你是一个英文翻译专家，可以把任意语言翻译为地道的美国英文，请帮我把下文翻译为地道易懂的美国英文，要求简单易懂，尽量不使用生僻的语法和字。",
        "zh": "你是一个中文翻译专家，可以把任意语言翻译为地道的中文普通话，请帮我把下文翻译为地道易懂的普通话，要求简单易懂，尽量不使用生僻的语法和繁体字。",
        "ru": "你是一个俄语翻译专家，可以把任意语言翻译为地道的俄语，请帮我把下文翻译为地道易懂的俄语，要求简单易懂，尽量不使用生僻的语法和字。",
        "ja": "你是一个日语翻译专家，可以把任意语言翻译为地道的日语，请帮我把下文翻译为地道易懂的日语，要求简单易懂，尽量不使用生僻的语法和字。",
        "de": "你是一个德语翻译专家，可以把任意语言翻译为地道的德语，请帮我把下文翻译为地道易懂的德语，要求简单易懂，尽量不使用生僻的语法和字。",
        "fr": "你是一个法语翻译专家，可以把任意语言翻译为地道的法语，请帮我把下文翻译为地道易懂的法语，要求简单易懂，尽量不使用生僻的语法和字。"
    }

    def __init__(self, api_key, model="glm-4-flash", timeout=10):
        self.api_key = api_key
        self.client = ZhipuAI(api_key=self.api_key)
        self.model = model if model else self.model
        self.timeout = timeout

    def translate(self, user_content, target_language):
        self.user_content = user_content
        self.target_language = target_language
        self.system_content = self.language_system_contents.get(self.target_language, "")
        self.task_id = None
        self.task_status = ''
        self.assistant_content = ''

        # 提交任务
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
                break

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


if __name__ == "__main__":
    api_key = "418234312598633f63b857c945a47f1f.x3jeQyzDJNk9KXJ4"
    translator = ZhipuAiTranslate(api_key, timeout=30)

    # 示例翻译
    text_to_translate = '''      
    智谱AI 开放平台提供一系列具有不同功能和定价的大模型，包括通用大模型、超拟人大模型、图像大模型、向量大模型等，并且支持使用您的私有数据对模型进行微调。 监控您的网站，展示状态（包括每日历史记录），并在网站状态发生变化时收到 Slack 通知。使用 Cloudflare Workers、CRON 触发器和 KV 存储。基于 Cloudflare Worker 的无服务器站点监控工具， 支持 HTTP/HTTPS/TCP 多种协议的端口监控， 可以从全球数百个城市发起地理位置特定的检查， 自定义的请求参数和响应校验规则,灵活适配各类监控场景。 
    规范一些代码文件和目录的命名，添加智谱AI翻译接口。
    '''
    translation_to_en = translator.translate(text_to_translate, "en")  # 设置超时时间为30秒（实际在初始化时设置了10秒）
    logging.info(f"Translation to English: {translation_to_en}")

    # text_to_translate_en = '''
    # It is indeed noteworthy that the United States seems to exhibit a distinct approach regarding accountability for actions taken by different entities. The impact of the case may be mostly symbolic given that Sinwar is believed to be hiding in tunnels in Gaza and the Justice Department says three of the six defendants are believed now to be dead. But officials say additional actions are expected as part of a broader effort to target a militant group that the U.S. designated as a foreign terrorist organization in 1997 and that over the decades has been linked to a series of deadly attacks on Israel, including suicide bombings.
    # '''
    # translation_to_zh = translator.translate(text_to_translate_en, "zh")  # 设置超时时间为30秒（实际在初始化时设置了10秒）
    # logging.info(f"Translation to Chinese: {translation_to_zh}")

    # 更多语言的翻译示例
    # ...