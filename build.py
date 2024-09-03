import re
import shutil
import subprocess
import zipfile
import os
import platform


class PythonCompiler:
    def __init__(self, script_name, icon_path, data_dir, version_info):
        self.script_name = script_name
        self.output_dir = f'{os.path.splitext(script_name)[0]}.dist'  # 输出目录
        self.icon_path = icon_path
        self.data_dir = data_dir
        self.version_info = version_info  # 版本信息

        # 将 Windows 和 x64 设为变量
        self.platform_name = 'Windows'
        self.architecture = 'x64'

        # 自动识别当前目录下的 venv\Scripts\python.exe
        self.python_executable = os.path.join(os.getcwd(), 'venv', 'Scripts', 'python.exe')
        self.nuitka_version = self.get_nuitka_version()

        # 定义压缩包文件名
        self.zip_filename = f'{os.path.splitext(script_name)[0]}_{self.platform_name}_{self.architecture}_v{self.version_info}.zip'

    def get_nuitka_version(self):
        """获取 Nuitka 版本并提取版本号"""
        nuitka_version_output = subprocess.check_output(
            [self.python_executable, '-m', 'nuitka', '--version']).decode().strip()
        return re.search(r'(\d+\.\d+\.\d+)', nuitka_version_output).group(0)

    def create_env_info(self):
        """创建环境信息文件"""
        env_info = f"""编译信息:
    - Python 版本: {platform.python_version()}
    - Nuitka 版本: {self.nuitka_version}
    - 操作系统: {platform.system()} {platform.release()}
    - 架构: {self.architecture}
    """

        with open('env_info.txt', 'w', encoding='utf8') as f:
            f.write(env_info)

    def compile(self):
        """运行 Nuitka 编译"""
        self.create_env_info()

        # nuitka_command = [
        #     self.python_executable, '-m', 'nuitka',
        #     '--msvc=latest',
        #     '--follow-imports',
        #     '--standalone',
        #     '--enable-plugin=tk-inter',
        #     '--windows-console-mode=disable',
        #     f'--include-data-dir={self.data_dir}/={self.data_dir}/',
        #     f'--windows-icon-from-ico={self.icon_path}',
        #     '--include-data-file=env_info.txt=env_info.txt',  # 包含环境信息文件
        #     self.script_name
        # ]

        nuitka_command = [
            self.python_executable, '-m', 'nuitka',
            '--msvc=latest',
            '--follow-imports',
            '--standalone',
            '--enable-plugin=tk-inter',
            f'--include-data-dir={self.data_dir}/={self.data_dir}/',
            f'--windows-icon-from-ico={self.icon_path}',
            '--include-data-file=env_info.txt=env_info.txt',  # 包含环境信息文件
            self.script_name
        ]

        subprocess.run(nuitka_command)

    def create_zip(self):
        """创建压缩包"""
        try:
            with zipfile.ZipFile(self.zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.output_dir):
                    for file in files:
                        zipf.write(
                            os.path.join(root, file),
                            os.path.relpath(os.path.join(root, file), self.output_dir)
                        )

            print(f'压缩包 {self.zip_filename} 创建成功。')
            return self.zip_filename
        except Exception as e:
            print(f'压缩包创建失败: {e}')
            return None

    def move_zip_file(self, destination):
        """移动 zip 文件到指定目录，覆盖已存在的同名文件"""
        destination_file_path = os.path.join(destination, os.path.basename(self.zip_filename))

        # 如果目标路径中已存在同名文件，则删除
        if os.path.exists(destination_file_path):
            try:
                os.remove(destination_file_path)
                print(f'已删除现有文件: {destination_file_path}')
            except Exception as e:
                print(f'删除现有文件失败: {e}')
                return

        try:
            shutil.move(self.zip_filename, destination)
            print(f'压缩包已移动到: {destination}')
        except Exception as e:
            print(f'移动压缩包失败: {e}')

    def run(self):
        """执行整个编译和压缩过程"""
        self.compile()
        return self.create_zip()


# 使用示例
if __name__ == "__main__":
    compiler = PythonCompiler(
        script_name='EPUBTranslatorUI.py',
        icon_path='static/pictures/favicon.ico',
        data_dir='static',
        version_info='2.0.6'
    )

    zip_file = compiler.run()
    print(f'生成的压缩文件: {zip_file}')