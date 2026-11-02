# Agent 面试学习手册 · 同例教学 v3

本分支保存基于 [Zchary1106/agent-interview-hub](https://github.com/Zchary1106/agent-interview-hub) 整理的离线 HTML 教材。

**下载 [完整 v3 压缩包](agent-interview-course-v3.zip)，解压后双击 `开始学习.html`。** 请保留整个文件夹，站内文件使用相对路径。GitHub 中直接点击 HTML 会显示源码，本分支没有部署在线网站。

## 内容

- 26课：原理讲解 → 同一案例演示 → 对应代码 → 变式练习。
- 109篇完整原文HTML，保留原仓库174文件快照与MIT许可。
- 486个问答条目及参考解；不同题库可能包含重复考点。
- 26个Python标准库实验，含完整参考程序、预期输出和扩展答案。
- 52个原实验/边界场景、262帧案例回放，逐帧关联正文与真实代码行。
- 41张源SVG、3个补充交互演示，以及搜索、作答记录、自评和导入导出。

## 目录

- [学习手册说明](<agent-interview-course 3/README.md>)
- [学习入口源码](<agent-interview-course 3/site/index.html>)
- [26课源码](<agent-interview-course 3/site/lessons/>)
- [可运行实验](<agent-interview-course 3/site/labs/>)
- [教学内容与生成器](<agent-interview-course 3/authoring/>)
- [来源覆盖清单](<agent-interview-course 3/manifest.json>)
- [验收记录](<agent-interview-course 3/authoring/QA.md>)

学习文件夹保留现有名称 `agent-interview-course 3`，无需改名；压缩包内的顶层文件夹名为 `agent-interview-course`。

## 本地运行与维护

普通阅读只需浏览器；实验建议Python3.10+，无需API Key。需要本地HTTP预览时，在学习文件夹内执行：

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

访问 `http://127.0.0.1:8765/site/index.html`。

修改教材以 `authoring/lessons/*.json` 为内容源，然后执行 `python3 authoring/build.py`。详细构建、测试和校验命令见学习手册说明与QA记录。

## 来源与边界

源快照提交：`e5b92617455e5ecc105162a22a42796c3041162d`，保存日期2026-11-01。原资料许可见 [MIT LICENSE](<agent-interview-course 3/source/LICENSE>)；新增教程与实验单独标识为教学补充。

面经和公司题含作者编辑及二手资料，不等同已核实的公司官方真题。案例回放使用预设数据，小实验验证机制，不是完整生产系统或真实模型训练。学习记录为本人自评，不能保证录用。
