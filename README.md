# 公众号活动稿蒸馏助手 / write-wechat-article-from-minutes

`write-wechat-article-from-minutes` 是一个面向活动报道、公众号推文和飞书文档交付的 Codex Skill。它适合处理“活动海报 + 飞书妙记/逐字稿/会议录音”这类材料，帮助使用者从原始会议内容中提炼事实、校正人名和单位口径，写出更像真人编辑过的公众号稿，并在需要时创建飞书文档做交付。

这个 Skill 的重点放在“可发布”三个字上：标题要稳，事实要清楚，段落要顺，敏感或未核实的信息要收住，最后还要确认飞书文档里确实落了正文。

## 发布地址

- GitHub: https://github.com/guiltyluce/write-wechat-article-from-minutes
- SkillHub: https://skillhub.cn/skills/write-wechat-article-from-minutes
- v1.0.0 Release: https://github.com/guiltyluce/write-wechat-article-from-minutes/releases/tag/v1.0.0

## 适合场景

- 活动结束后，根据海报和飞书妙记写公众号推文。
- 把会议录音、妙记、纪要整理成活动报道或新闻稿。
- 对人名、单位名、项目名、公司名做公开信息交叉核验。
- 修正妙记转写中的同音字、OCR 误读和议程口径偏差。
- 写完稿后，把成稿同步到飞书文档并做回读校验。

## 能力边界

这个 Skill 会优先使用原始逐字稿和海报事实，不把 AI 纪要当成唯一来源。遇到人物职务、单位名称、项目成果、产品能力等容易变化或容易误写的信息，会要求使用公开来源核验。查不到一手来源时，应保留原材料口径，并提示发布前由主办方确认。

它不会替用户虚构活动效果，也不会把私密电话、内部客户对齐内容、竞品比较细节直接写进公开稿，除非用户明确要求保留。

## 目录结构

```text
.
├── README.md
├── VERSION
├── CHANGELOG.md
├── LICENSE
├── scripts/
│   └── validate_skill_package.py
└── skill/
    └── write-wechat-article-from-minutes/
        ├── SKILL.md
        ├── agents/
        │   └── openai.yaml
        └── write-wechat-article-from-minutes.zip
```

## 安装

如果你的运行时支持本地 Skill 目录，可以直接复制 Skill 文件夹：

```bash
mkdir -p ~/.codex/skills
cp -R skill/write-wechat-article-from-minutes ~/.codex/skills/
```

也可以使用打包后的 zip：

```text
skill/write-wechat-article-from-minutes/write-wechat-article-from-minutes.zip
```

## 使用方式

给出活动海报、本地图片路径或飞书妙记链接后，直接说明目标即可：

```text
用 write-wechat-article-from-minutes，根据这张海报和这个妙记写一篇公众号推文，并落到飞书文档。
```

Skill 会引导 Codex 完成以下动作：

- 读取海报和妙记基础信息。
- 导出逐字稿与 AI 章节作为证据材料。
- 根据公开来源核验单位、人员、项目和产品名。
- 写成公众号风格稿件。
- 如需飞书交付，创建文档并回读确认正文已写入。

## 打包与校验

项目不依赖第三方 Python 包。建议使用 Python 3.10 或更高版本。

```bash
python3 scripts/validate_skill_package.py --zip
```

通过后会看到类似输出：

```text
[ok] wrote zip: skill/write-wechat-article-from-minutes/write-wechat-article-from-minutes.zip
[ok] write-wechat-article-from-minutes skill package validated
```

校验内容包括：

- `SKILL.md` frontmatter 中的 `name` 与目录名一致。
- `description` 足够具体，能触发正确任务。
- `agents/openai.yaml` 包含展示名、短描述和默认提示。
- SkillHub/GitHub 分发 zip 可正常解压并通过完整性检查。

## 发布口径

这个 Skill 面向内容生产和办公提效场景。它只提供写作工作流和事实核验纪律，不替代主办方最终审稿。正式发布前，建议由活动主办方确认人名、职务、单位名称、合作关系和可公开范围。

## License

MIT
