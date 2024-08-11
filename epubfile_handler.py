import os
import shutil
import zipfile
from pathlib import Path
from .pcolors import pcolors  # 假设你有一个pcolors.py文件

class FileHandler:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_name = ''
        self.file_extracted_path = ''

    def get_file_info(self):
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"The file {self.file_path} does not exist.")
        self.file_name = os.path.splitext(os.path.basename(self.file_path))[0]
        self.file_extracted_path = os.path.join(os.path.abspath(os.path.join(self.file_path, os.pardir)), self.file_name + '_translated')
        self._prepare_extracted_path()

    def _prepare_extracted_path(self):
        if os.path.exists(self.file_extracted_path):
            shutil.rmtree(self.file_extracted_path)
        os.makedirs(self.file_extracted_path)

    def extract(self):
        try:
            with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
                print('Extracting the epub file...', end='\r')
                zip_ref.extractall(self.file_extracted_path)
                print(f'Extracting the epub file: [{pcolors.GREEN} DONE {pcolors.ENDC}]')
            return True
        except Exception as e:
            print(f'Extracting the epub file: [{pcolors.FAIL} FAIL {pcolors.ENDC}] - {e}')
            return False

    def zip(self):
        print('Making the translated epub file...', end='\r')
        try:
            filename = f"{self.file_extracted_path}.epub"
            with open(Path(self.file_extracted_path) / 'mimetype', 'w') as file:
                file.write('application/epub+zip')
            with zipfile.ZipFile(filename, 'w') as archive:
                archive.write(Path(self.file_extracted_path) / 'mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
                for file in Path(self.file_extracted_path).rglob('*.*'):
                    archive.write(file, file.relative_to(Path(self.file_extracted_path)), compress_type=zipfile.ZIP_DEFLATED)
            shutil.rmtree(self.file_extracted_path)
            print(f'Making the translated epub file: [{pcolors.GREEN} DONE {pcolors.ENDC}]')
        except Exception as e:
            print(e)
            print(f'Making the translated epub file: [{pcolors.FAIL} FAIL {pcolors.ENDC}]')