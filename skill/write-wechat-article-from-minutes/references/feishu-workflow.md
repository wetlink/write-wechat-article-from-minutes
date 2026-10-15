# 飞书读取、写入与回读

本参考用于实际读取妙记或交付飞书文档。若用户已提供逐字稿且只需要文字，可跳过飞书操作。

## 选择可用工具

优先使用已连接、已授权的飞书工具。使用 `lark-cli` 时，读取本机相应 `lark-shared`、`lark-minutes`、`lark-vc`、`lark-doc` 技能及本次操作需要的参考。缺少这些技能时，通过当前 CLI 帮助或官方文档确认用法；不能假定本仓库已包含连接器、凭证或其他技能。

以下示例的文档接口使用 v2，发布时已核对当前 CLI 帮助。运行环境不同，应以实际帮助为准：

```bash
lark-cli doctor
lark-cli vc +notes --help
lark-cli docs +create --api-version v2 --help
lark-cli docs +update --api-version v2 --help
lark-cli docs +fetch --api-version v2 --help
```

默认使用用户身份 `--as user`。授权过期或权限不足时，沿用工具的授权流程，不切换到另一身份扩大访问。不要输出或保存访问令牌到稿件、日志或公共仓库。

## 提取妙记

从用户链接提取 minute token，再读取实际转写：

```bash
lark-cli vc +notes --as user \
  --minute-tokens MINUTE_TOKEN \
  --output-dir ./work/minutes \
  --format json
```

只在确认覆盖已有导出符合当前任务时使用 `--overwrite`。多份妙记按返回的文件路径逐份读取，记录素材覆盖范围；先用摘要定位，再核对原始段落。不要将“录音已转写”等同于“整场活动已有完整材料”。

## 创建文档

先明确目标是新建文档还是更新用户提供的现有文档。正文采用适合编辑的简单标题和段落；编稿状态可用独立说明块，无须为普通文章强行加入表格或流程图。

用户提供 Markdown 文件或要求 Markdown 导入时：

```bash
lark-cli docs +create --api-version v2 --as user \
  --doc-format markdown --content @work/article.md --dry-run

lark-cli docs +create --api-version v2 --as user \
  --doc-format markdown --content @work/article.md
```

其他场景可按 `lark-doc` 默认使用 DocxXML：

```bash
lark-cli docs +create --api-version v2 --as user \
  --doc-format xml --content @work/article.xml
```

XML 文档用唯一的 `title` 元素设置标题。文件路径须相对于当前工作目录；长文本使用 `@file` 或 stdin，避免在命令行拼接正文。不要使用旧版 `--markdown`、`--mode` 示例。

创建成功后保存返回的文档 URL 或 token。写入结果不明确时，先确认是否已创建，再决定重试。

## 更新现有文档

先回读目标章节，保留用户增补、图片、批注和其他已有内容。一次修订涉及全篇日期时，检查导语、正文、编稿说明、结尾和朋友圈；不要只替换首次出现的日期。将回读返回的整数 `revision_id` 保存为 `DOCUMENT_REVISION`，写入时传入该版本作为基准。

```bash
lark-cli docs +fetch --api-version v2 --as user \
  --doc DOC_URL --scope keyword --keyword '待补|前两日|活动时间' \
  --detail with-ids

lark-cli docs +update --api-version v2 --as user \
  --doc DOC_URL --command block_replace --block-id BLOCK_ID \
  --revision-id "$DOCUMENT_REVISION" \
  --doc-format xml --content @work/section.xml
```

遇到版本冲突时，重新读取并合并用户期间的改动，不自动改用最新版本参数覆盖。若连接器不支持版本约束，写入前复核目标内容并尽量缩小修改范围。结构修改后重新获取 block ID，不能继续假定旧 ID 有效。只有用户明确要求整篇替换且内容已经核对时，才使用 `overwrite`。追加内容前先确认目标中尚未存在，避免重复段落。

## 验证交付

```bash
lark-cli docs +fetch --api-version v2 --as user \
  --doc DOC_URL --detail full
```

短稿可读全文；长稿先检查目录和受影响章节。确认返回的正文、标题、必要更正及待补状态与本次交付一致；若更新了多个位置，应逐处核对。

写入成功已获明确响应、但回读失败时，可说明“写入已获成功响应，正文回读未完成”。写入请求超时或结果不明、回读也未完成时，说明“写入状态未确认”，先查询目标状态，不盲目重试。两种情况都不能宣称已验证。此工作流只交付飞书文档，不自动发布到公众号或向他人发送消息。
