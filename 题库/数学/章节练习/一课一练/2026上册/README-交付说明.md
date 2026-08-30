# 2026《高中数学·一课一练》上册题库交付包 V1.0

## 当前状态

本目录包含第1—9章共9个独立的 `V1.0_REVIEWED_FROZEN` ZIP。整书共有106课、1,378题和2,822个图片资产。

每章均已完成：

- 题目与答案配对复核；
- 公式、分数、指数、图形和跨页边界复核；
- 人工区域修正及变更题二次确认；
- Schema 1.1、资源、孤立文件、图片解码、尺寸、字节数和哈希校验；
- 两次独立确定性 ZIP 构建，结果字节完全一致。

本目录状态为“可进入真实 MathBank 导入验收”，不等同于已经完成正式导入或生产发布。

## 文件说明

- `MATH_YKYL2026_U1_C01...C09_V1.0_REVIEWED_FROZEN.zip`：九个章节冻结包。
- `delivery-manifest.json`：机器可读的整书、章节、数量、大小、哈希和后续任务状态。
- `SHA256SUMS.txt`：九个 ZIP 的交付哈希基线。
- `NEXT-TASK-HANDOFF.md`：后续模型或任务的直接承接说明。
- `delivery-validation.json`：交付目录复制与一致性验证结果。

## 使用约束

1. 不要解压后重新压缩、改名、覆盖或修改这些冻结 ZIP。
2. 导入前必须重新计算 SHA-256，并与 `SHA256SUMS.txt` 和 `delivery-manifest.json` 同时比对。
3. 按第1章到第9章顺序执行导入测试，并记录导入器版本、运行环境和每章结果。
4. 导入产生的日志、数据库、截图和学习记录应写入新的测试工作目录，不要写回本交付目录。
5. 如果任一 ZIP 哈希不一致，应停止导入并回到源 Task 核查，不能用新压缩包替换哈希基线。
6. 本交付包不含源 PDF、扫描页、复核图片、OCR 缓存或临时构建目录。

## 可追溯知识

GitHub 仓库：`https://github.com/johnny025021/AI-OS-Test`

主要入口：

- `02-Knowledge/AI-Knowledge/04-Methods/Verified Scan Exercise-Book Question Bank Production Method.md`
- `01-Projects/Learning-System/Subject-Self-Study-System/Tasks/TASK-20260820-COMPUTER-A-001/Task.md`

知识提交：`daf796785b21a20e7f3818db57ffccc208756038`

交付创建时最新记录提交：`de36e05a18dfa0a14a1773b446946468753a1c99`

## 推荐下一步

建立一个新的 MathBank 导入验收任务，按照 `NEXT-TASK-HANDOFF.md` 执行。验收通过后，再单独决定正式题库目录、备份位置和发布授权。
