import requests
from .pcolors import pcolors  # 假设你有一个pcolors.py文件，存放颜色类

class ToolUpdater:
    @staticmethod
    def check_for_updates():
        try:
            release_api = 'https://api.github.com/repos/quantrancse/epub-translator/releases/latest'
            response = requests.get(release_api, headers={'user-agent': 'Mozilla/5.0'}, timeout=5).json()
            latest_release = response['tag_name'][1:]
            if TOOL_VERSION != latest_release:
                print(f'Current tool version: {pcolors.FAIL}{TOOL_VERSION}{pcolors.ENDC}')
                print(f'Latest tool version: {pcolors.GREEN}{latest_release}{pcolors.ENDC}')
                print(f'Please upgrade the tool at: {pcolors.CYAN}https://github.com/quantrancse/epub-translator/releases{pcolors.ENDC}')
                print('-' * LINE_SIZE)
        except Exception:
            print('Something was wrong. Cannot get the tool latest update!')