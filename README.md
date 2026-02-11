# 抖音关注列表个人简介批量获取工具

批量获取你的抖音关注列表中所有用户的个人简介，并自动筛选出包含漫展行程信息的 coser。

## 功能

- 通过 Playwright 控制系统 Chrome 浏览器，拦截抖音 API 响应
- 自动收集所有关注用户的昵称、简介、粉丝数等信息
- 按漫展相关关键词（漫展/CP/BW/签售/行程等）过滤出有行程的 coser
- 输出三个文件：完整 JSON 数据、简介汇总、漫展行程筛选结果

## 环境要求

- Python 3.10+
- 系统已安装 Chrome 浏览器
- Playwright (`pip install playwright`)

## 使用方法

```bash
cd D:\Git\douyin-follow-bio
python fetch_followings.py
```

1. 脚本会打开 Chrome 浏览器，先手动登录抖音
2. 登录后回到终端按回车
3. 脚本跳转到你的关注页面，手动向下滚动加载所有关注
4. 滚动到底后回到终端按回车，脚本保存结果

## 输出文件

| 文件 | 说明 |
|------|------|
| `output/all_followings.json` | 所有关注用户的完整数据 |
| `output/bio_summary.txt` | 所有用户的昵称+简介汇总 |
| `output/coser_events.txt` | 筛选出包含漫展行程关键词的用户 |

## 原理

利用 Playwright 的网络拦截功能，监听浏览器向抖音 API (`/user/following/list/`) 发出的请求响应，自动提取数据。这样不需要处理 `a_bogus` 等签名参数，浏览器自己会搞定。
