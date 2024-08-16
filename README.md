![Python Version][python-shield]
[![MIT License][license-shield]][license-url]

# EPUB Translator 文档

## 介绍

EPUB Translator 是一个用于翻译 EPUB 文件的工具，能够提取、翻译章节内容，并将翻译后的内容重新打包成 EPUB 文件。该工具支持多线程和多进程处理，提升翻译效率，并提供详细的日志记录功能。

## 功能

- 解压 EPUB 文件并提取 XHTML 文件。
- 通过翻译 API 翻译章节内容。
- 将翻译后的内容重新打包成 EPUB 文件。
- 支持多线程和多进程以提高性能。
- 日志记录功能，记录翻译过程中的信息和错误。

## 安装

### 依赖项

- Python 3.6 及以上版本。

### 克隆项目

```bash
git clone https://github.com/shiqianwei0508/epub-translator.git
cd epub-translator
```

### 安装依赖

```bash
pip install -r requirements.txt
```

## 使用说明

### 命令行参数

运行 EPUB Translator 时，可以使用以下命令行参数：

```bash
python epub_translator.py [EPUB 文件路径] [OPTIONS]
```

#### 必需参数

- `file_paths`: 一个或多个 EPUB 文件的路径。

#### 可选参数

- `--http_proxy`: HTTP 代理（例如：http://your.proxy:port）。
- `--gtransapi_suffixes`: API 后缀的逗号分隔列表（例如："com,com.tw,co.jp,com.hk"）。
- `--dest_lang`: 目标语言（例如：zh-cn）。
- `--transMode`: 翻译模式，1 表示仅翻译文本，2 表示返回原文和翻译文本（默认 1）。
- `--TranslateThreadWorkers`: 翻译线程工作数（默认 16）。
- `--processes`: EPUB 章节并行处理进程数（默认 4）。
- `--log_file`: 日志文件路径（默认: app.log）。
- `--log_level`: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
- `--tags_to_translate`: 需要翻译的标签内容（例如："h1,h2,h3,title,p"）。

### 示例

```bash
python epub_translator.py my_book.epub --http_proxy http://your.proxy:port --gtransapi_suffixes com,com.tw --dest_lang zh-cn
```

### 配置文件

您还可以使用 `config.ini` 配置文件来指定参数。配置文件的格式如下：

```ini
[Translation]
gtransapi_suffixes = com,com.tw,co.jp,com.hk
tags_to_translate = h1,h2,h3,title,p
dest_lang = zh-cn
http_proxy = http://your.proxy:port
transMode = 1
TranslateThreadWorkers = 16
processes = 4

[Logger]
log_file = app.log
log_level = INFO

[Files]
epub_file_path = path/to/your.epub
```

## 代码结构

- `EPUBTranslator`: 主要翻译逻辑的实现，包括 EPUB 文件的处理和翻译功能。
- `ConfigLoader`: 加载配置文件的类，用于读取命令行参数和配置文件中的参数。
- `main()`: 主程序入口，处理命令行参数、加载配置并启动翻译器。

## 日志

日志会记录在指定的日志文件中，您可以通过调整 `log_level` 参数来控制日志的详细程度。

## 信号处理

该工具支持 SIGINT 信号处理，您可以通过按 `Ctrl+C` 中断程序，程序将进行清理操作并退出。

## 贡献

欢迎任何形式的贡献！请通过提交问题（issues）或拉取请求（pull requests）来参与。

## 许可证

该项目遵循 MIT 许可证，请查看 LICENSE 文件以获取更多信息。

## 联系信息

如需更多帮助或信息，请联系 [sqwei2012@gmail.com]。
