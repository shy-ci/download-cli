# download-cli

用一个命令下载大文件或慢速文件。底层使用 [aria2](https://aria2.github.io/) 的 HTTP 分段并发下载、断点续传和自动重试；`download-cli` 提供简单的参数和可选的完整性校验。

## 安装

需要 Python 3.9+ 和 `aria2c`。

```bash
# macOS
brew install aria2

# Ubuntu / Debian
sudo apt install aria2

python3 -m pip install git+https://github.com/shy-ci/download-cli.git
```

也可以克隆仓库后直接运行 `python3 download_cli.py URL`，无需安装 Python 包。

## 使用

```bash
# 自动使用 URL 中的文件名，保存到当前目录
download-cli 'https://example.com/large-file.zip'

# 指定保存路径和并发连接数
download-cli 'https://example.com/large-file.zip' -o ~/Downloads/large-file.zip -c 16

# 下载中断后，重新运行完全相同的命令即可续传
download-cli 'https://example.com/large-file.zip' -o ~/Downloads/large-file.zip -c 16

# 有官方 SHA-256 值时，让 aria2 校验下载结果
download-cli 'https://example.com/large-file.zip' --sha256 '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'

# macOS DMG：下载完成后验证磁盘映像
download-cli 'https://example.com/App.dmg' -d ~/Downloads --verify-dmg

# 慢连接：增加重试次数、等待时间和空闲超时
download-cli 'https://example.com/large-file.zip' --retries 50 --retry-wait 10 --timeout 120

# 限速，避免占满网络
download-cli 'https://example.com/large-file.zip' --max-speed 2M
```

查看全部参数：`download-cli --help`。

## 工作方式与限制

- 并发指的是多个 HTTP 连接分别下载文件的不同字节区间，并非把一个连接变快。服务器支持 `Range` 请求时效果最好；不支持时 aria2 会退回单连接下载。
- aria2 在目标文件旁保存 `.aria2` 控制文件。下载未完成时不要删除它；再次运行相同命令可从已下载部分继续。完成后它会自动删除。
- 默认 16 个连接；连接数并非越高越快。有些服务器会限速或拒绝过多连接，可试 `-c 4` 或 `-c 8`。
- 断点续传依赖服务器支持范围请求以及下载资源保持不变。若服务端文件已更换，请删除旧文件及其 `.aria2` 控制文件后重下。
- `--sha256` 需要可信来源提供的正确摘要。没有摘要时，程序只能确认传输完成；DMG 可用 `--verify-dmg` 做磁盘映像校验。
- 本工具适合公开可直接访问的 HTTP(S) 文件。带登录态、临时签名或防盗链的链接可能需要重新获取可用 URL。

## 这次 Antigravity 下载的命令

```bash
download-cli 'https://storage.googleapis.com/antigravity-public/antigravity-hub/2.32.2-4665802025205760/darwin-arm/Antigravity.dmg' \
  -o ~/Downloads/Antigravity.dmg -c 16 --verify-dmg
```
