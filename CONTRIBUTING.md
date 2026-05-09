# 贡献指南

欢迎一起改进雅思 AI 私教。这个项目的目标很明确：做一个本地运行、用户自带大模型接口、帮助 IELTS 学习者制定计划和复盘进步的桌面工具。

## 可以贡献什么

- 修复安装、启动、打包问题
- 改进中文界面和新手文档
- 优化每日计划、写作批改、复盘报告的提示词
- 补充真实运行截图、教程视频或使用案例

## 不接受什么

- 内置第三方教材、音频、PDF、OCR 文本或官方练习内容
- 提交任何真实 API Key、`.env`、SQLite 数据库或个人学习记录
- 宣称提供 IELTS 官方评分或官方保证
- 把云端账号系统、远程数据收集作为默认能力

## 本地开发

从项目根目录启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-app.ps1
```

如果只改前端，可以进入桌面应用目录：

```powershell
cd apps\desktop
npm install
npm run dev
```

如果只改后端，可以进入后端目录：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_backend.py
```

## 提交前检查

建议至少运行：

```powershell
node --check apps\desktop\src\api.js
node --check apps\desktop\electron\main.cjs
py -m compileall -q backend\app backend\smoke_test.py backend\integration_test.py
```

如果改动涉及 AI 调用，建议再运行集成测试：

```powershell
py backend\integration_test.py
```

## 提交 Pull Request

PR 描述建议写清楚：

- 改了什么
- 为什么要改
- 如何验证
- 是否影响隐私、API Key、学习数据或打包流程
