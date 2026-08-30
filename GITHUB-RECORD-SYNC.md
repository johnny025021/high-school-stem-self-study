# GitHub 学习记录同步

## 仓库隔离

- 公开仓库：`high-school-stem-self-study`，保存网页、在线目录和题库 ZIP。
- 私有仓库：`stembank-learning-records`，只保存学生学习记录。
- 不得把真实学习记录、访问令牌或其他凭据提交到公开仓库。

## 私有仓库准备

1. 创建私有仓库 `stembank-learning-records`，初始化 `main` 分支和 README。
2. 创建只允许访问该仓库的细粒度访问令牌。
3. Repository permissions 仅授予 Contents 的读取和写入权限。
4. 在数学网页点击“GitHub记录同步”，填写仓库和令牌，点击“保存并同步”。

网页保存路径为：

```text
records/math/STUDENT_001/latest.json
```

物理、化学接入完整页面后分别使用 `records/physics/...` 和 `records/chemistry/...`，不会混入数学记录。

## 同步规则

- 页面启动且已有授权时，先下载远程 `latest.json`，按不可变 `event_id` 合并到本机 IndexedDB。
- 合并后把本机与远程的事件并集写回私有仓库。
- 新增作答或题目反馈后延迟约一分钟同步，连续答题期间不会每题产生一次 Git 提交。
- 点击“立即同步”可马上执行双向合并。
- 同一个学习者必须在不同设备上使用相同 `profile_id`。
- 同一 `event_id` 内容冲突时停止合并，避免覆盖不确定记录。

## Pad 使用

- iPad 或安卓 Pad 首次连接时需要输入一次细粒度令牌。
- 只在学生个人设备上勾选“记住在这台个人设备上”。
- 公共或临时设备不要记住令牌，使用结束后点击“断开连接”。
- “分享/下载记录 JSON”独立于 GitHub 同步，始终可作为人工备份和紧急迁移通道。
