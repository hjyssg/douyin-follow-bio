# 任务清单

## 背景
每天关注抖音关注列表中 coser 的个人简介变化，因为 coser 会在简介中更新漫展行程。

## 已完成

- [x] 分析已有的 `doujson_follow_list.json` 数据结构
  - 来源：抖音 Web API `/aweme/v1/web/user/following/list/`
  - 每页 20 条
  - 关键字段：`nickname`（昵称）、`signature`（个人简介）、`sec_uid`、`uid`
- [x] 确认系统环境：Chrome + Edge 已安装，Python 3.13 可用
- [x] 安装 Playwright（`pip install playwright`）
- [x] 编写 `fetch_followings.py` 主脚本（网络拦截方案）

## 待完成

- [x] 更新 `fetch_followings.py` 为网络拦截方案
  - 监听浏览器 API 响应，而非主动 fetch
  - 绕过 `a_bogus` / `msToken` 签名问题
- [x] 使用 `channel="chrome"` 直接用系统 Chrome（不需要下载 Playwright 浏览器驱动）
- [ ] 首次运行测试
- [ ] 验证数据完整性（是否能拿到全部关注）
- [ ] 检查漫展关键词过滤效果，按需调整关键词列表

## 后续优化方向

- [ ] 自动滚动：用 Playwright 自动模拟滚动，不需要手动操作
- [ ] 定时运行：每天自动执行，对比简介变化
- [ ] 简介变更通知：对比前后两次结果，高亮变化的简介
- [ ] 支持导出为 Excel/CSV
