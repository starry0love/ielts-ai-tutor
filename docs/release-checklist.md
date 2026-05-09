# Release 发布清单

这份清单用于发布 GitHub Release 前自查。

## 发布前

- [ ] 确认 `.env`、SQLite 数据库、打包缓存没有进入 Git
- [ ] 确认 README 和新手攻略能说明“用户需要自备大模型接口”
- [ ] 确认仓库不包含第三方教材、音频、PDF、OCR 文本或练习内容
- [ ] 运行后端 Python 编译检查
- [ ] 运行前端基础语法检查
- [ ] 至少用一个模拟 OpenAI-compatible 服务跑通集成测试

## 打包

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package-exe.ps1
```

产物目录：

```text
apps\desktop\dist-electron
```

## GitHub Release 文案模板

标题：

```text
雅思 AI 私教 0.1.0
```

说明：

```markdown
首次开源版本。

这个版本提供本地运行的 IELTS AI 学习导师：

- 用户自行连接 OpenAI-compatible 大模型接口
- 支持入门画像、今日计划、写作批改、每日复盘、学习进度、周/月报
- 不内置 API Key
- 不内置第三方教材、音频、PDF、OCR 文本或练习内容
- 学习数据默认保存在本机 SQLite 数据库

下载便携版后运行，第一次打开按界面引导填写自己的大模型接口信息。
```

## 自动发布

推送版本标签后，GitHub Actions 会自动构建 Windows 便携版并创建 Release：

```powershell
git tag v0.1.0
git push origin v0.1.0
```

如果只是日常代码提交，不需要打标签。
