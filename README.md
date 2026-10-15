# 公众号活动稿写作助手

[![Version](https://img.shields.io/badge/version-1.1.0-blue)](https://github.com/wetlink/write-wechat-article-from-minutes/releases/tag/v1.1.0)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

从海报、飞书妙记、逐字稿和会议纪要中提取事实，核对公开信息，写成公众号文章；按需附朋友圈文案并交付飞书文档。

`write-wechat-article-from-minutes` 是供 Codex 等支持本地技能的助手使用的写作方法包。它规定怎样取证、取舍和审稿，飞书访问与网络检索由运行环境提供。

## 能处理什么

- **活动报道**：将多份素材整理成一篇文章，校正人名、机构名与转写误差。
- **企业外宣**：以公司的受邀发言、业务实践和实际贡献为中心，按用户要求控制活动背景的篇幅。
- **多日活动续稿**：区分活动总日期与素材覆盖日期，先交付阶段稿，再接续第三日等新增材料。
- **公开内容筛选**：剔除内部复盘、客户对齐及私人闲聊，不替与会者编造表态。
- **朋友圈文案**：另写简短文案，保持事实、立场和活动进度一致。
- **飞书交付**：创建或更新文档，并实际回读正文确认交付。

## 安装

从 [v1.1.0 Release](https://github.com/wetlink/write-wechat-article-from-minutes/releases/tag/v1.1.0) 下载 `write-wechat-article-from-minutes.zip`，解压后将整个技能目录放入运行环境的技能目录。

也可以克隆指定版本，以下命令适用于首次安装到尚不存在的目标目录：

```bash
git clone --branch v1.1.0 https://github.com/wetlink/write-wechat-article-from-minutes.git
cd write-wechat-article-from-minutes
mkdir -p ~/.codex/skills
cp -R skill/write-wechat-article-from-minutes ~/.codex/skills/
cp VERSION LICENSE ~/.codex/skills/write-wechat-article-from-minutes/
```

已有同名技能时，先确认它是否由其他仓库或软链接管理，再在其源目录更新。不要覆盖已维护的定制版本。安装后重新加载助手的技能列表。

## 使用

在支持技能调用的助手中，提供材料并说明目标：

```text
用 $write-wechat-article-from-minutes，依据这份海报和两个妙记链接，
写一篇约1000字的公众号稿，附一段朋友圈文案，并落到飞书文档。
```

```text
用 $write-wechat-article-from-minutes，改写这篇活动报道。
我方是特邀演讲嘉宾，重点写公司的AI实践。
不要收录录音后半段的内部客户对齐内容。
```

```text
用 $write-wechat-article-from-minutes，先整理现有两天的材料。
活动总共三天，第三天材料待补。先写入现有飞书文档，标明阶段稿。
```

完整的匿名材料与阶段稿示例见 [examples/staged-event.md](skill/write-wechat-article-from-minutes/examples/staged-event.md)。

## 环境要求

写作本身需要能读取所给材料的 AI 助手。公开核验需要网络检索能力；飞书读取和交付需要用户已授权的连接器或 `lark-cli`。

本项目不捆绑飞书凭证，也不自动安装其他技能。使用 CLI 时，建议配合环境中的 `lark-shared`、`lark-minutes`、`lark-vc` 和 `lark-doc`，并先检查实际命令帮助。[飞书操作参考](skill/write-wechat-article-from-minutes/references/feishu-workflow.md) 已采用文档 v2 接口示例。

## 写作规则

海报说明活动安排，逐字稿支持实际发言，公开资料用于交叉核验名称和背景。AI摘要与旧稿作为线索；未经证实的出席、签约、成效和未来承诺不能写实。

稿件以具体事实和清晰表达为主，减少重复排比、空泛评价和固定的“不是……而是……”句式。核验问题放在审稿区，阶段稿注明待补范围。创建飞书文档不等于向公众号发布，正式发文须另有授权。

## 版本与验证

当前版本 **1.1.0**，变更见 [CHANGELOG.md](CHANGELOG.md)。采用语义化版本号：兼容的能力新增升次版本，修正升补丁版本，不兼容的工作流调整升主版本。`VERSION` 是版本来源，发布标签使用 `v` 前缀。

打包与验证仅依赖 Python 3.10 及以上版本的标准库：

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/validate_skill_package.py --zip
```

分发包包含技能正文、界面元数据、参考、匿名示例、版本号和许可证。校验检查结构、引用与压缩包完整性，不代替实际任务中的事实核验和飞书回读。

## 项目结构

```text
README.md
VERSION
CHANGELOG.md
LICENSE
scripts/
  validate_skill_package.py
  test_validate_skill_package.py
skill/write-wechat-article-from-minutes/
  SKILL.md
  agents/openai.yaml
  references/feishu-workflow.md
  examples/staged-event.md
  write-wechat-article-from-minutes.zip
```

公开仓库只维护通用写作规则与虚构示例，不收录真实录音、内部文档或客户材料。本次 `v1.1.0` 发布到 GitHub；其他技能平台的版本状态需另行确认。

## License

[MIT](LICENSE)
