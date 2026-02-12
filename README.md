# 抖音关注列表个人简介批量获取工具

批量获取你的抖音关注列表中所有用户的个人简介，自动筛选出包含漫展行程信息的 coser。

## 功能

- 通过 Playwright 连接 Chrome 调试端口，拦截抖音 API 响应
- 自动收集所有关注用户的昵称、简介、粉丝数等信息
- 抓取完成后自动解析简介，筛选并打印含漫展/线下行程的用户
- 每次运行按日期存档到 `output/YYYY-MM-DD/` 子目录

## 环境要求

- Python 3.10+
- 系统已安装 Chrome 浏览器
- Playwright (`pip install playwright`)

## 使用方法

```bash
python fetch_followings.py
```

1. 脚本自动关闭 Chrome 并以调试模式重启
2. 在 Chrome 中登录抖音，进入个人主页，点击「关注」
3. 在关注列表弹窗中不断向下滚动，加载所有关注
4. 终端实时显示捕获进度，滚动到底后回到终端按回车
5. 自动保存数据并打印漫展行程汇总

也可以单独运行解析（会自动找最新日期目录的数据）：

```bash
python parse_bio.py
```

## 输出文件

每次运行保存到 `output/YYYY-MM-DD/` 目录下：

| 文件 | 说明 |
|------|------|
| `all_followings.json` | 所有关注用户的完整数据 |
| `raw_responses.json` | API 原始响应 |
| `bio_summary.txt` | 所有用户的昵称+简介汇总 |

## 原理

利用 Playwright 连接 Chrome 调试端口，通过 CDP 监听网络事件，捕获浏览器向抖音 API (`/user/following/list/`) 发出的请求响应。不需要处理 `a_bogus` 等签名参数，浏览器自己会搞定。

`parse_bio.py` 使用关键词匹配 + 日期正则从简介中识别漫展行程，覆盖常见漫展名（萤火虫、SSCA、IJOY、世界线等）和行程相关词汇。
