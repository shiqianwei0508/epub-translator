import os
import zipfile


def extract_epub(epub_file, output_dir):
    with zipfile.ZipFile(epub_file, 'r') as zip_ref:
        zip_ref.extractall(output_dir)
    print(f'Extracted {epub_file} to {output_dir}')


def create_epub_from_directory(input_dir, output_file):
    # 先创建一个新的 EPUB 文件
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # 只写入 mimetype 文件，确保它是第一个文件且不压缩
        zip_ref.write(os.path.join(input_dir, 'mimetype'), 'mimetype', compress_type=zipfile.ZIP_STORED)

        # 遍历目录，写入所有其他文件
        for foldername, subfolders, filenames in os.walk(input_dir):
            for filename in filenames:
                if filename == 'mimetype':
                    continue  # 跳过 mimetype 文件，避免重复添加
                # 计算相对路径
                file_path = os.path.join(foldername, filename)
                # 添加文件到 ZIP
                zip_ref.write(file_path, os.path.relpath(file_path, input_dir))
    print(f'Created {output_file} from {input_dir}')


# 示例用法
epub_file = 'Python编程与初级数学.epub'  # 输入的 EPUB 文件名
output_dir = 'Python编程与初级数学_translated'  # 解压缩目录
output_epub = 'Python编程与初级数学001.epub'  # 新的 EPUB 文件名

# 解压 EPUB 文件
extract_epub(epub_file, output_dir)

# 压缩目录为新的 EPUB 文件
create_epub_from_directory(output_dir, output_epub)