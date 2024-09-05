import logging


class Logger:
    def __init__(self, log_file='app.log', level=logging.DEBUG):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # 创建文件处理器，并设置为覆盖模式
        file_handler = logging.FileHandler(log_file, mode='w', encoding="utf-8")  # 使用 'w' 模式清空文件
        file_handler.setLevel(level)

        # 设置控制台处理器格式为 ColoredFormatter
        console_formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        # 设置文件处理器格式为普通的 Formatter
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        # 将处理器添加到 logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)