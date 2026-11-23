# download-cli

用一个命令下载大文件或慢速文件。普通文件使用 [aria2](https://aria2.github.io/) 做 HTTP 分段并发；`.m3u8` 视频流使用 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 做 HLS 分片并发。两种方式都支持断点续传和重试。

## macOS 安装与使用

需要 Python 3.9+、[Homebrew](https://brew.sh/) 和 `aria2c`。下载 HLS 视频流还需要安装 yt-dlp：

```bash
brew install aria2
python3 -m pip install --user -U yt-dlp
python3 -m pip install --user https://github.com/shy-ci/download-cli/archive/refs/heads/main.zip
download-cli 'https://example.com/large-file.zip' -d ~/Downloads -c 16
```

如果安装后提示找不到 `download-cli`，可以改用下面的“直接运行源码”方式。

## Windows 安装与使用

需要 [Python 3.9+](https://www.python.org/downloads/windows/) 和 `aria2c.exe`。普通文件需要 aria2；HLS 视频流需要 yt-dlp。到 [aria2 官方发布页](https://github.com/aria2/aria2/releases)下载适合自己系统的 Windows ZIP，解压后把 **`aria2c.exe` 所在文件夹**加入 Windows 的 `Path` 环境变量。重新打开 CMD 或 PowerShell，先检查：

```powershell
py --version
aria2c --version
py -m yt_dlp --version
```

然后在 PowerShell 中安装并下载：

```powershell
py -m pip install --user https://github.com/shy-ci/download-cli/archive/refs/heads/main.zip
py -m pip install --user -U yt-dlp
download-cli 'https://example.com/large-file.zip' -d "$HOME\Downloads" -c 16
```

下载 `.m3u8` 视频时，当前 yt-dlp 需要 Python 3.11 或更新版本。CMD 示例：

```cmd
py download_cli.py "https://example.com/video/index.m3u8" -o "第20261115期.mp4" -d "E:\nowgogogo" -c 8
```

工具会把 `-c 8` 作为 8 个 HLS 分片并发数传给 yt-dlp。指定 `.mp4` 时会请求转封装为 MP4，需要系统已安装 FFmpeg。

如果 `py` 不存在，尝试把上述 `py` 换成 `python`。如果安装后提示找不到 `download-cli`，可以改用下面的“直接运行源码”方式。

### 直接运行源码（两种系统通用）

从本仓库的 **Code → Download ZIP** 下载源码并解压。进入解压后的文件夹，再运行：

```bash
# macOS 终端
python3 download_cli.py 'https://example.com/large-file.zip' -d ~/Downloads
```

```powershell
# Windows PowerShell
py .\download_cli.py 'https://example.com/large-file.zip' -d "$HOME\Downloads"
```

这种方式无需安装 Python 包，但仍需要 `aria2c` 可在命令行中找到。

## Linux 安装

以 Ubuntu / Debian 为例：

```bash
sudo apt install aria2
python3 -m pip install --user -U yt-dlp
python3 -m pip install --user https://github.com/shy-ci/download-cli/archive/refs/heads/main.zip
```

## 使用

```bash
# 自动使用 URL 中的文件名，保存到当前目录
download-cli 'https://example.com/large-file.zip'

# 普通文件：指定保存路径和 HTTP 并发连接数
download-cli 'https://example.com/large-file.zip' -o ~/Downloads/large-file.zip -c 16

# HLS 视频：并发下载 8 个分片，并转封装为 MP4（需要 FFmpeg）
download-cli 'https://example.com/video/index.m3u8' -o ~/Downloads/video.mp4 -c 8

# 下载中断后，重新运行完全相同的命令即可续传
download-cli 'https://example.com/large-file.zip' -o ~/Downloads/large-file.zip -c 16

# 有官方 SHA-256 值时，让 aria2 校验下载结果
download-cli 'https://example.com/large-file.zip' --sha256 '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'

# macOS DMG：下载完成后验证磁盘映像（Windows 不使用此参数）
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
- 普通文件默认 8 个 HTTP 连接；HLS 视频默认 8 个并发分片。连接数并非越高越快，有些服务器会限速或拒绝过多并发，可试 `-c 4`。
- HLS 视频需要安装 yt-dlp：Windows 用 `py -m pip install -U yt-dlp`，macOS/Linux 用 `python3 -m pip install -U yt-dlp`。这里的 `-c` 会传给 yt-dlp 的 HLS 分片并发参数；它和 aria2 的 HTTP Range 连接是两种并发方式。
- 断点续传依赖服务器支持范围请求以及下载资源保持不变。若服务端文件已更换，请删除旧文件及其 `.aria2` 控制文件后重下。
- `--sha256` 需要可信来源提供的正确摘要。没有摘要时，程序只能确认传输完成；DMG 可用 `--verify-dmg` 做磁盘映像校验。
- 本工具适合公开可直接访问的 HTTP(S) 文件。带登录态、临时签名或防盗链的链接可能需要重新获取可用 URL。

## 这次 Antigravity 下载的命令

下面是 **Mac ARM 版**下载命令；Windows 应换成软件提供的 Windows 安装包链接，不要下载这个 DMG。

```bash
download-cli 'https://storage.googleapis.com/antigravity-public/antigravity-hub/2.32.2-4665802025205760/darwin-arm/Antigravity.dmg' \
  -o ~/Downloads/Antigravity.dmg -c 16 --verify-dmg
```
