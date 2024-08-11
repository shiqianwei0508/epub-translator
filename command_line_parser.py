import argparse

class CommandLineParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description='A tool for translating epub files to different languages using Google Translate, with support for custom dictionaries.')
        self._setup_arguments()

    def _setup_arguments(self):
        self.parser.add_argument('-v', '--version', action='version', version='epub-translator v%s' % TOOL_VERSION)
        self.parser.add_argument('epub_file_path', type=str, help='path to the epub file')
        self.parser.add_argument('-l', '--lang', type=str, metavar='dest_lang', help='destination language')
        self.parser.add_argument('-d', '--dict', type=str, metavar='dict_path', help='path to the translation dictionary')

    def parse(self):
        return self.parser.parse_args()