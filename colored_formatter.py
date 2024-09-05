import logging


class ColoredFormatter(logging.Formatter):
    # 定义颜色
    COLORS = {
        'DEBUG': '\033[94m',     # 蓝色
        'INFO': '\033[92m',      # 绿色
        'WARNING': '\033[93m',   # 黄色
        'ERROR': '\033[91m',     # 红色
        'CRITICAL': '\033[41m',  # 红色背景
        'RESET': '\033[0m',      # 重置颜色
    }

    def format(self, record):
        # 获取日志级别
        level_name = record.levelname
        # 获取对应颜色
        color = self.COLORS.get(level_name, self.COLORS['RESET'])
        # 设置记录的消息为彩色
        record.msg = f"{color}{record.msg}{self.COLORS['RESET']}"
        return super().format(record)