# 浏览器数据库规划

三个学科使用独立 IndexedDB 名称，防止升级、清理和数据迁移相互影响：

- 数学：`general_learning_question_bank_stem_math_v1`
- 物理：`general_learning_question_bank_stem_physics_v1`
- 化学：`general_learning_question_bank_stem_chemistry_v1`

本目录只保存数据库结构、迁移说明和离线备份工具，不直接保存浏览器内部数据库文件。
