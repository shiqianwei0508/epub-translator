# Clash 代理节点切换工具

这是一个用于自动切换 Clash 代理节点的 Python 脚本。该脚本会首先将流量切换到指定的代理组，然后在该组中循环切换代理节点。

## 依赖

- Python 3
- `requests` 库

## 使用方法

1. **安装 `requests` 库**
   
   在终端中运行以下命令来安装 `requests` 库：

   ```
   pip install requests
   ```

2. **运行脚本**

   在终端中，运行以下命令来启动代理节点切换：

   ```
   python clash_operator.py --group-name <代理组名称> [--api-url <API 地址>] [--api-token <API 令牌>] [--delay <切换延迟>]
   ```

   其中：

   - `<代理组名称>`：（必需）要切换的代理组名称。
   - `<API 地址>`：（可选）Clash API 地址，默认为 `http://localhost:9090`。
   - `<API 令牌>`：（可选）Clash API Token，如果需要的话。
   - `<切换延迟>`：（可选）每次切换代理节点的延迟时间（秒），默认为 30 秒。

## 示例

以下命令将每 60 秒在 "MyProxyGroup" 代理组中切换一次代理节点：

```
python clash_operator.py --group-name MyProxyGroup --delay 60
```

如果 Clash API 需要 Token，并且运行在一个不同的地址，你可以使用 `--api-url` 和 `--api-token` 参数，例如：

```
python clash_operator.py --group-name MyProxyGroup --delay 60 --api-url http://192.168.1.100:9090 --api-token mysecrettoken
```

## 注意事项

- 请确保 Clash API 是可访问的，并且提供了正确的 API Token（如果需要的话）。
- 脚本会在每次切换节点时打印一条日志消息，如果遇到任何问题，这些消息可能会有所帮助。