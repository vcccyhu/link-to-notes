# Link to Notes｜小红书视频素材库 Skill


**0.2.2-preview：个人项目预发布版。32项本地程序检查、真实小红书样本、WorkBuddy主流程和Obsidian模板已有实测；Windows、Linux、豆包与陌生用户盲测未验证。**


项目背景和个人贡献见 [项目说明](docs/PROJECT.md)，逐项证据与限制见 [发布验收报告](docs/RELEASE_TEST_REPORT.md)，输出格式见 [自制演示](examples/README.md)。


把小红书视频分享文本整理为本地可检索笔记：标题、作者、封面、发布时间、点赞快照、原链接和真实文字稿集中保存。按“标题 — 作者”命名，自定义分类。适合素材积累及选定一批视频分析。它不是独立App，也不保证平台每一条视频都能取得。


## 阅读格式与图文支持

默认输出易读标题、封面资料、AI总结、来源正文和备注。原标题保留，平台ID仅作后台去重。图文笔记由智能体读取全部图片后生成逐页要点，并保存来源图片，不冒充视频文字稿。详见 [阅读格式](references/reading-format.md)。

本次更新为Skill工作流说明；采集程序仍只自动处理带中文字幕的视频。总结、阅读标题、图文及无字幕后备需要具有相应能力的智能体执行。既有0.2.1的32项程序检查不能代替0.2.2在所有宿主重新安装验收。

## 安装与首次使用


1. 下载或克隆本仓库。GitHub仓库名为 `link-to-notes`，导入前将解压后的项目文件夹命名为 `xiaohongshu-video-library`，再把完整文件夹导入支持本地Skill的智能体。Codex可放到用户的 `.codex/skills/xiaohongshu-video-library/` 目录；其他宿主按自己的导入方式，不能导入时先参照兼容性文档做能力测试。
2. 需要Python 3.10以上、curl，以及基础Python依赖。建议在本文件夹建独立虚拟环境：


```sh
python -m venv .venv
```


Windows激活：`.venv\Scripts\Activate.ps1`；macOS/Linux激活：`source .venv/bin/activate`。若系统命令是 `python3`，使用它代替 `python`。激活后：


```sh
python -m pip install -r requirements.txt
python scripts/doctor.py
```


doctor首次提示尚未设置位置是正常的。让智能体使用这个虚拟环境的Python，不能假定宿主自动激活。doctor只检查，不自动安装。


3. 告诉智能体：“使用这个Skill，先把我的素材库设在我指定的文件夹；分类先待分类。”或者给出自己的类别。也可手动执行：


```sh
python scripts/library_config.py init --root '你选择的素材库文件夹' --categories '英语学习' '销售工作'
```


不加类别即先待分类；选自媒体预设用 `--preset creator`，二者不同时用。目录允许中文和空格。初始化只创建缺失文件，重跑不覆盖已有配置和规则。后续修改类别时同步素材库中的 `索引/收纳设置.json` 和 `索引/分类规则.md`。


4. 发整段分享文本并说“收纳这条”。手动检查也可运行：


```sh
python scripts/collect_link.py '这里粘贴整段小红书分享文本'
```


只有绑定中文字幕的路径已在采集程序中自动化；无字幕时智能体需要继续执行音频后备，不是脚本自行完成。详细步骤见 [工作流](references/workflow.md)。


测试时可用 `library_config.py init --root '测试文件夹' --config '独立配置.json'`，然后只在本次进程设置 `XHS_LIBRARY_CONFIG` 指向该文件，避免覆盖原有配置。也可始终显式传 `--root`。


## 无字幕转写的可选依赖


需要ffmpeg和ffprobe在可执行路径中，以及：


```sh
python -m pip install -r requirements-asr.txt
