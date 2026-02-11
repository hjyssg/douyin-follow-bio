# 抖音关注列表个人简介批量获取工具

批量获取你的抖音关注列表中所有用户的个人简介，并自动筛选出包含漫展行程信息的 coser。

## 功能

- 通过 Playwright 控制系统 Chrome 浏览器，拦截抖音 API 响应
- 自动收集所有关注用户的昵称、简介、粉丝数等信息
- 按漫展相关关键词（漫展/CP/BW/签售/行程等）过滤出有行程的 coser
- 解析简介，提取漫展/线下活动行程，支持生成 LLM prompt 做结构化提取

## 环境要求

- Python 3.10+
- 系统已安装 Chrome 浏览器
- Playwright (`pip install playwright`)

## 使用方法

### 1. 抓取关注列表

```bash
python fetch_followings.py
```

1. 脚本会自动关闭 Chrome 并以调试模式重启
2. 在 Chrome 中登录抖音，进入个人主页，点击「关注」
3. 在关注列表弹窗中不断向下滚动，加载所有关注
4. 终端会实时显示捕获进度，滚动到底后回到终端按回车保存

### 2. 解析简介 & 提取行程

```bash
# 默认模式：筛选含行程信息的用户，输出汇总
python parse_bio.py

# 输出结构化 JSON
python parse_bio.py --json

# 生成 LLM prompt，可粘贴给 ChatGPT/Claude 提取结构化行程数据
python parse_bio.py --prompt

# 显示所有用户（含无行程的）
python parse_bio.py --all
```

## 输出文件

| 文件 | 说明 |
|------|------|
| `output/all_followings.json` | 所有关注用户的完整数据 |
| `output/raw_responses.json` | API 原始响应 |
| `output/bio_summary.txt` | 所有用户的昵称+简介汇总 |
| `output/schedule_summary.txt` | 含漫展/行程信息的用户汇总 |
| `output/schedule_users.json` | 含行程用户的结构化 JSON（`--json` 模式） |
| `output/extract_schedule_prompt.txt` | LLM 提取 prompt（`--prompt` 模式） |

## 原理

利用 Playwright 连接 Chrome 调试端口，通过 CDP 监听网络事件，捕获浏览器向抖音 API (`/user/following/list/`) 发出的请求响应。这样不需要处理 `a_bogus` 等签名参数，浏览器自己会搞定。

`parse_bio.py` 使用关键词匹配 + 日期正则从简介中识别漫展行程，覆盖常见漫展名（萤火虫、SSCA、IJOY、世界线等）和行程相关词汇。
