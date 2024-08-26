import os
import tkinter as tk  # 导入tkinter模块
from tkinter import filedialog, messagebox  # 导入文件对话框和消息框模块
from tkinter.ttk import Progressbar, Label, Entry, Button, Checkbutton, Radiobutton, Frame  # 导入ttk组件
import logging  # 导入logging模块以记录日志
import threading  # 导入threading模块以支持多线程
import queue  # 导入queue模块用于线程间通信

from epubTranslator import EPUBTranslator  # 导入EPUBTranslator类


class EPUBTranslatorUI:
    def __init__(self, master):
        self.master = master  # 设置主窗口
        self.master.title("EPUB Translator")  # 设置窗口标题
        self.master.iconbitmap('static/pictures/favicon.ico')   # 设置logo
        self.create_widgets()  # 创建窗口小部件
        self.translation_thread = None  # 初始化翻译线程
        self.queue = queue.Queue()  # 初始化队列用于线程间通信

    def create_widgets(self):
        # 标签和输入框的配置
        Label(self.master, text="EPUB 文件路径（以逗号分隔）:").grid(row=0, column=0, sticky="w")  # 标签
        self.epub_path_entry = Entry(self.master, width=50)  # 输入框
        self.epub_path_entry.grid(row=0, column=1)  # 输入框的布局

        # 创建选择文件按钮
        self.select_files_button = Button(self.master, text="选择文件", command=self.select_files)  # 按钮
        self.select_files_button.grid(row=0, column=2)  # 按钮的布局

        # 修改HTTP代理的布局，使其更紧凑
        Label(self.master, text="HTTP 代理 - IP地址:").grid(row=1, column=0, sticky="w")  # 标签
        self.proxy_ip_entry = Entry(self.master, width=20)  # 输入框，用于输入IP地址
        self.proxy_ip_entry.insert(0, "127.0.0.1")  # 设置默认值为127.0.0.1
        self.proxy_ip_entry.grid(row=1, column=1, sticky="w")  # 布局IP地址输入框

        Label(self.master, text="端口:").grid(row=1, column=2, sticky="w")  # 标签
        self.proxy_port_entry = Entry(self.master, width=10)  # 输入框，用于输入端口
        self.proxy_port_entry.insert(0, "7890")  # 设置默认值为7890
        self.proxy_port_entry.grid(row=1, column=3, sticky="w", padx=(0, 20))  # 布局端口输入框

        Label(self.master, text="要使用的API后缀:").grid(row=2, column=0, sticky="w")  # 标签
        self.api_suffixes = ["com", "com.hk", "com.tw", "co.jp", "com.sg", "co.uk"]  # 标签列表
        self.api_suffix_vars = {tag: tk.BooleanVar(value=True) for tag in self.api_suffixes}  # 创建每个标签的BooleanVar

        # 创建一个框架来包含API后缀复选框
        api_suffixes_frame = Frame(self.master)  # 创建一个框架
        api_suffixes_frame.grid(row=2, column=1, sticky="w")  # 布局框架

        # 创建复选框
        for i, api_suffix in enumerate(self.api_suffixes):
            Checkbutton(api_suffixes_frame, text=api_suffix, variable=self.api_suffix_vars[api_suffix]).grid(row=i, sticky="w")  # 布局复选框

        Label(self.master, text="目标语言:").grid(row=4, column=0, sticky="w")  # 标签
        # 创建目标语言单选按钮
        self.dest_lang_var = tk.StringVar(value="zh-cn")  # 默认值为中文
        Radiobutton(self.master, text="中文", variable=self.dest_lang_var, value="zh-cn").grid(row=4, column=1,
                                                                                               sticky="w")  # 中文单选按钮
        Radiobutton(self.master, text="英文", variable=self.dest_lang_var, value="en").grid(row=4, column=2, sticky="w")  # 英文单选按钮


        # 添加翻译模式单选按钮
        self.trans_mode_var = tk.IntVar(value=1)  # 默认值为1
        Label(self.master, text="翻译模式:").grid(row=5, column=0, sticky="w")  # 标签
        Radiobutton(self.master, text="仅目标语言", variable=self.trans_mode_var, value=1).grid(row=5, column=1, sticky="w")  # 单选按钮1
        Radiobutton(self.master, text="双语模式", variable=self.trans_mode_var, value=2).grid(row=5, column=2, sticky="w")  # 单选按钮2

        Label(self.master, text="文本翻译线程数量:").grid(row=6, column=0, sticky="w")  # 标签
        self.thread_workers_entry = Entry(self.master, width=50)  # 输入框
        self.thread_workers_entry.insert(0, "8")  # 设置默认值为8
        self.thread_workers_entry.grid(row=6, column=1)  # 输入框的布局

        Label(self.master, text="章节并行处理线程数量:").grid(row=7, column=0, sticky="w")  # 标签
        self.processes_entry = Entry(self.master, width=50)  # 输入框
        self.processes_entry.insert(0, "8")  # 设置默认值为8
        self.processes_entry.grid(row=7, column=1)  # 输入框的布局

        Label(self.master, text="日志文件路径:").grid(row=8, column=0, sticky="w")  # 标签
        self.log_file_entry = Entry(self.master, width=50)  # 输入框

        # 获取用户的下载文件夹路径
        downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")  # 获取下载文件夹路径
        default_log_file_path = os.path.join(downloads_folder, "epubTranslate.log")  # 设置默认日志文件路径
        self.log_file_entry.insert(0, default_log_file_path)  # 设置输入框默认值

        self.log_file_entry.grid(row=8, column=1)  # 输入框的布局

        # 创建选择文件按钮
        self.select_log_file_button = Button(self.master, text="选择文件", command=self.select_log_file)  # 按钮
        self.select_log_file_button.grid(row=8, column=2)  # 按钮的布局

        # 创建一个框架来包含日志级别单选按钮
        log_level_frame = Frame(self.master)  # 创建一个框架
        log_level_frame.grid(row=9, column=0, columnspan=3, sticky="w")  # 布局框架

        Label(log_level_frame, text="日志级别:").grid(row=0, column=0, sticky="w")  # 标签
        self.log_level_var = tk.StringVar(value="INFO")  # 默认值为INFO
        logging_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]  # 日志级别列表
        for i, level in enumerate(logging_levels):
            Radiobutton(log_level_frame, text=level, variable=self.log_level_var, value=level).grid(row=0, column=i + 1, sticky="w")  # 单选按钮

        Label(self.master, text="要翻译的标签:").grid(row=10, column=0, sticky="w")  # 标签
        self.tags = ["title", "h1", "h2", "h3", "span", "p", "a", "li"]  # 标签列表
        self.tag_vars = {tag: tk.BooleanVar(value=True) for tag in self.tags}  # 创建每个标签的BooleanVar

        # 创建一个框架来包含标签复选框
        tags_frame = Frame(self.master)  # 创建一个框架
        tags_frame.grid(row=11, column=0, columnspan=3, sticky="w")  # 布局框架

        # 创建复选框
        for i, tag in enumerate(self.tags):
            Checkbutton(tags_frame, text=tag, variable=self.tag_vars[tag]).grid(row=0, column=i, padx=5, pady=5, sticky="w")  # 布局复选框

        # 创建动态进度条
        Label(self.master, text="翻译中，请等待：").grid(row=12, column=0, sticky="w")  # 标签
        self.progress = Progressbar(self.master, orient="horizontal", length=300, mode="indeterminate")  # 创建动态进度条
        self.progress.grid(row=12, column=1, columnspan=2)  # 布局进度条

        # 创建翻译按钮
        self.translate_button = Button(self.master, text="开始翻译", command=self.run_translation)  # 按钮
        self.translate_button.grid(row=14, column=0, columnspan=3)    # 按钮的布局

    def select_files(self):
        # 打开文件选择对话框，允许选择多个EPUB文件
        file_paths = filedialog.askopenfilenames(title="选择EPUB文件", filetypes=[("EPUB Files", "*.epub")])  # 选择文件
        if file_paths:  # 如果用户选择了文件
            current_paths = self.epub_path_entry.get()
            new_paths = ",".join(file_paths)  # 获取新选择的文件路径
            self.epub_path_entry.insert(tk.END, ("," + new_paths) if current_paths else new_paths)  # 添加新路径

    def select_log_file(self):
        # 打开文件选择对话框，允许用户选择或创建日志文件
        file_path = filedialog.asksaveasfilename(
            title="选择日志文件",
            defaultextension=".log",
            filetypes=[("Log Files", "*.log"), ("All Files", "*.*")]
        )  # 选择文件
        if file_path:  # 如果用户选择了文件
            self.log_file_entry.delete(0, tk.END)  # 清空输入框
            self.log_file_entry.insert(tk.END, file_path)  # 将选择的文件路径插入输入框

    def run_translation(self):
        # 检查是否已有翻译线程在运行
        if self.translation_thread and self.translation_thread.is_alive():  # 如果翻译线程存在并且仍在运行
            messagebox.showwarning("警告", "翻译已经在进行中，请等待完成。")  # 显示警告信息
            return  # 退出方法，不启动新的翻译线程

            # 检查 EPUB 文件路径是否为空
        if not self.epub_path_entry.get():
            messagebox.showerror("错误", "请提供至少一个EPUB文件路径。")
            return

            # 检查目标语言是否为空
        if not self.dest_lang_var.get():
            messagebox.showerror("错误", "请提供目标语言。")
            return

        # 禁用所有按钮
        self.toggle_buttons(tk.DISABLED)

        # 把开始翻译按钮修改为"正在翻译，请耐心等待。。。"
        self.translate_button.config(text="正在翻译，请耐心等待!")


        # 启动一个新线程进行翻译
        self.translation_thread = threading.Thread(target=self.start_translation)  # 直接调用start_translation
        self.translation_thread.start()  # 启动线程

        # 显示正在翻译的消息框
        # messagebox.showinfo("信息", "正在翻译。。。请查看进度。")


        # 启动进度条更新
        self.update_progress_bar()

    def start_translation(self):
        # 获取输入框的内容
        epub_paths = self.epub_path_entry.get().split(",")  # 获取EPUB文件路径并分割

        # 获取HTTP代理IP和端口，并组合成"http://IP:端口"格式
        proxy_ip = self.proxy_ip_entry.get()  # 获取HTTP代理的IP地址
        proxy_port = self.proxy_port_entry.get()  # 获取HTTP代理的端口
        http_proxy = f"http://{proxy_ip}:{proxy_port}"  # 合并成"http://IP:端口"格式

        api_suffixes_use_list = [api_suffix for api_suffix, var in self.api_suffix_vars.items() if
                                 var.get()]  # 获取选中的API后缀
        api_suffixes_use = ",".join(api_suffixes_use_list)  # 以逗号分隔的字符串

        dest_lang = self.dest_lang_var.get()  # 获取目标语言（现在是单选框的值）

        trans_mode = self.trans_mode_var.get()  # 获取翻译模式（1或2）
        thread_workers = int(self.thread_workers_entry.get() or 1)  # 获取翻译线程工作数，默认为1
        processes = int(self.processes_entry.get() or 1)  # 获取并行处理进程数，默认为1
        log_file = self.log_file_entry.get()  # 获取日志文件路径
        log_level = self.log_level_var.get()  # 获取日志级别
        tags_to_translate_list = [tag for tag, var in self.tag_vars.items() if var.get()]  # 获取选中的标签
        tags_to_translate = ",".join(tags_to_translate_list)  # 以逗号分隔的字符串

        # 设置日志级别，使用默认级别如果提供的级别无效
        log_level = getattr(logging, log_level, logging.INFO)  # 获取日志级别

        # 创建并运行EPUB翻译器
        translator = EPUBTranslator(
            epub_paths,
            processes,
            http_proxy,
            log_file,
            log_level,
            api_suffixes_use,
            dest_lang,
            trans_mode,
            thread_workers,
            tags_to_translate
        )

        try:
            translator.translate()  # 调用翻译方法
            messagebox.showinfo("成功", "翻译已完成！")  # 显示成功信息
        except Exception as e:  # 捕获错误
            messagebox.showerror("错误", f"翻译失败: {e}")  # 显示错误信息
        finally:
            self.toggle_buttons(tk.NORMAL)

            # 恢复开始翻译按钮显示
            self.translate_button.config(text="开始翻译")

    def update_progress_bar(self):
        if self.translation_thread.is_alive():  # 检查翻译线程是否仍在运行
            current_value = self.progress['value']  # 获取当前进度条的值
            new_value = (current_value + 10) % 100  # 增加10并保持在0到90之间
            if new_value > 90:
                new_value = 90  # 确保不超过90
            self.update_progress(new_value)  # 更新进度条的值
            self.master.after(500, self.update_progress_bar)  # 每500毫秒调用自身
        else:
            self.progress.stop()  # 停止进度条动画
            self.update_progress(100)  # 将进度条设置为100%

    def update_progress(self, value):
        self.progress['value'] = value  # 更新进度条的值
        self.master.update_idletasks()  # 更新界面

    def toggle_buttons(self, state):
        self.translate_button.config(state=state)
        self.select_log_file_button.config(state=state)
        self.select_files_button.config(state=state)


# 创建主窗口
if __name__ == "__main__":
    root = tk.Tk()  # 创建主窗口
    app = EPUBTranslatorUI(root)  # 初始化应用程序
    root.mainloop()  # 启动主循环
