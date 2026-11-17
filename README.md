# Link to Notes｜小红书视频素材库 Skill

**0.2.3-preview：个人项目预发布版。32项本地程序检查、真实小红书样本、WorkBuddy主流程和Obsidian模板已有实测；Windows、Linux、豆包与陌生用户盲测未验证。**

项目背景和个人贡献见 [项目说明](docs/PROJECT.md)，逐项证据与限制见 [发布验收报告](docs/RELEASE_TEST_REPORT.md)，输出格式见 [自制演示](examples/README.md)。

把小红书视频分享文本整理为本地可检索笔记：标题、作者、封面、发布时间、点赞快照、原链接和真实文字稿集中保存。按“标题 — 作者”命名，自定义分类。适合素材积累及选定一批视频分析。它不是独立App，也不保证平台每一条视频都能取得。

## 阅读格式与图文支持

默认输出易读标题、封面资料、AI总结、来源正文和备注。原标题保留，平台ID仅作后台去重。图文笔记由智能体读取全部图片后生成逐页要点，并保存来源图片，不冒充视频文字稿。详见 [阅读格式](references/reading-format.md)。

本次更新为Skill工作流说明；采集程序仍只自动处理带中文字幕的视频。总结、阅读标题、图文及无字幕后备需要具有相应能力的智能体执行。既有0.2.1的32项程序检查不能代替0.2.2在所有宿主重新安装验收。

## 跨窗口启动与权限

首次运行 `python scripts/bootstrap.py --setup`，后续窗口统一使用 `python scripts/bootstrap.py --check` 和 `python scripts/bootstrap.py --run collect_link -- '分享文案'`。它会复用Skill目录内的独立环境；缺依赖会给出修复步骤。不会自动改变系统代理、安全设置或宿主权限。首次安装与需要开放的具体权限见 [启动与权限说明](references/setup.md)。

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
```

ffmpeg请从官方发行渠道或所用系统的软件包管理器安装。首次转写需要联网下载模型，会用CPU、内存、临时磁盘；模型正常退出后删除，依赖安装缓存不会自动删除。输出是自动识别稿，需核对漏句，不是保证准确的人工逐字稿。

## 文件放在哪里

首次选择的位置保存为使用者本地的 `.config/xiaohongshu-video-library/config.json`，不包含在公开包里。优先级：显式 `--root`、环境变量 `XHS_LIBRARY_ROOT`、本地配置。`XHS_LIBRARY_CONFIG`可覆盖配置文件位置。没有设置时停止，不擅自保存到系统目录。

素材目录包含素材笔记、封面附件、索引、分析清单和测试记录。普通UTF-8 Markdown，无密码；Obsidian可选。需要总览时把素材库文件夹作为Obsidian仓库打开，使用支持Bases功能的版本；本版模板已在Obsidian 1.15.1本机空白仓库显示和筛选通过，跨机器仍待验收。不用Obsidian可直接打开Markdown与文字索引。

已有笔记不会因更新Skill而重装。保存前按平台ID去重，保留人工备注。当前不支持并发写同一素材库，批量收纳应逐条执行。

## 分类与分析

类别由使用者决定；先待分类也可以。延后分类模式累计10条时提示复核，提出方案后等待用户确认，不强制自动移动文件。分类按本条主线与用途判断，作者单独记录。

总览勾选“本次分析”或直接给出标题；智能体先固定本轮清单，再只分析选中的视频。分类属性与正文表格同步更新。

## 支持范围与发布边界

- 小红书短链接、完整分享文本、具体笔记链接：已有本机样本验证；平台结构、网络环境和登录状态变化可能失败。
- 音频识别：本地英语、中文样本验证；真实完全无字幕小红书端到端自动切换仍待验收。
- 抖音：仅一条人工辅助样本成功，未集成通用支持。
- WorkBuddy 5.11.3 / macOS 26.5.1：已安装0.2.0-preview的主流程真实验收通过，网络需单次诊断；本次0.2.1辅助程序的测试范围按报告记录。豆包、Windows与Linux仍**未验证**。参照 [兼容性与测试表](references/compatibility.md)，不承诺一个Skill文件即可在所有产品使用。

## 测试与分享

```sh
python -m unittest discover -s tests -v
```

完整回归包含ffmpeg音频标准化测试，需要安装可选转写依赖。测试仅使用自制合成数据；不访问真实账号。结果见 [修改记录](CHANGELOG.md)，接下来的发布验收见 [后续计划](docs/NEXT_STEPS.md)。

公开包不包含作者的素材库、实际视频全文、浏览器数据、登录凭据或本地配置。只收纳自己有权处理的内容，向外分享素材另行确认授权。本项目的MIT许可证覆盖代码与模板，不授予第三方视频素材的使用权。依赖不随包分发，遵循各自许可证。

## 0.2.3改进

修复Markdown链接识别，增加仅本机显式选择的网络请求偏好复用；新库默认只有素材笔记、封面附件、索引三个目录，其余按需创建。既有资料不会因升级删除。总结、分类与验证完成后明确停止；历史报告不作为新任务。自动化程序仍不负责生成AI总结，智能体需执行该步骤。此版本的停止规则不能保证消除宿主模型故障。
