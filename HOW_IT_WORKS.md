# 工作原理

## 一句话总结

脚本启动一个带"调试后门"的 Chrome，然后通过这个后门偷听 Chrome 和抖音服务器之间的对话，把关注列表数据存下来。

## 详细流程

```
┌─────────┐     ┌──────────┐     ┌──────────────┐
│  脚本    │────▶│  Chrome   │────▶│  抖音服务器   │
│ (Python) │     │ (调试模式) │     │              │
│          │◀───│          │◀───│              │
│  偷听数据 │     │  正常浏览  │     │  返回关注列表  │
└─────────┘     └──────────┘     └──────────────┘
```

### 第一步：启动调试模式的 Chrome

正常的 Chrome 是一个"黑盒"，外部程序无法知道它在干什么。但 Chrome 有一个隐藏功能：**远程调试端口**。

```
chrome.exe --remote-debugging-port=9222
```

加上这个参数后，Chrome 会在本机的 9222 端口开一个"后门"（技术上叫 WebSocket 服务），允许外部程序通过这个端口来观察和控制浏览器。

这就是 Chrome DevTools（F12 开发者工具）的底层原理——DevTools 本身也是通过这个协议和 Chrome 通信的。

### 第二步：Python 脚本连接到 Chrome

脚本使用 **Playwright** 库，通过 **CDP（Chrome DevTools Protocol）** 连接到 Chrome 的 9222 端口。

```python
browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
```

**名词解释：**
- **Playwright**：微软开发的浏览器自动化库，可以控制 Chrome/Firefox/Safari
- **CDP**：Chrome DevTools Protocol，Chrome 的调试协议，就是 F12 开发者工具用的那套协议
- **127.0.0.1**：本机地址（localhost），因为 Chrome 和脚本在同一台电脑上

### 第三步：开启网络监听

连接上之后，脚本通过 CDP 发送一条指令：

```python
cdp.send("Network.enable")
```

这相当于告诉 Chrome："把你所有的网络请求都告诉我"。就像在 F12 里打开 Network 面板一样。

然后脚本注册了两个事件监听：

1. **`Network.responseReceived`**：Chrome 收到服务器响应时触发。脚本检查 URL 里是否包含 `following/list`（抖音关注列表 API 的特征），如果是就记下这个请求的 ID。

2. **`Network.loadingFinished`**：响应数据完全下载完成时触发。脚本用之前记下的请求 ID，调用 `Network.getResponseBody` 获取完整的响应内容（JSON 数据）。

### 第四步：你在 Chrome 里操作

你正常使用 Chrome 浏览抖音，打开关注列表弹窗，向下滚动。每次滚动，抖音前端会自动向服务器请求下一页关注数据。

脚本在后台默默监听这些请求，每捕获到一页数据就：
- 解析 JSON，提取用户的昵称、简介、粉丝数等
- 在终端打印进度
- 修改 Chrome 标签页标题显示进度

### 第五步：保存数据

你按回车后，脚本把收集到的数据保存为三个文件：
- `raw_responses.json`：抖音 API 返回的原始 JSON（完整数据）
- `all_followings.json`：提取出的用户信息（昵称、简介等）
- `bio_summary.txt`：人类可读的简介汇总

## 为什么不直接调 API？

抖音的 API 有反爬虫机制，每个请求需要带 `a_bogus` 和 `msToken` 两个签名参数。这些参数是由抖音前端的 JavaScript 代码实时计算的，算法经常变化，很难逆向。

通过监听浏览器的方式，我们让抖音自己的前端代码去处理签名，脚本只是"旁听"已经完成的请求，完全不需要破解签名算法。

## 为什么要用独立的 profile 目录？

Chrome 的用户数据目录（User Data）有一个锁文件机制，同一时间只允许一个 Chrome 实例使用同一个目录。如果你的 Chrome 已经在运行（哪怕是后台进程），用同一个目录启动新实例时，`--remote-debugging-port` 参数会被忽略。

所以脚本使用独立的 `chrome_debug_profile` 目录，避免和你日常使用的 Chrome 冲突。代价是第一次需要重新登录抖音，但之后 cookie 会保存在这个目录里。

## 关键术语

| 术语 | 解释 |
|------|------|
| CDP | Chrome DevTools Protocol，Chrome 的调试协议 |
| Playwright | 微软的浏览器自动化库 |
| 远程调试端口 | Chrome 的 `--remote-debugging-port` 参数开启的 WebSocket 服务 |
| route 拦截 | 中间人模式，会修改/延迟请求（我们没用这个，因为会导致页面卡住） |
| Network 事件监听 | 纯被动监听模式，不干扰请求（我们用的是这个） |
| User Data 目录 | Chrome 存储用户配置、cookie、历史记录的文件夹 |
| a_bogus / msToken | 抖音的反爬虫签名参数 |
