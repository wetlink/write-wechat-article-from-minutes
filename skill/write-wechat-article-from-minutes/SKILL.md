---
name: write-wechat-article-from-minutes
description: Use when the user provides an event poster/image plus a Feishu/Lark Minutes URL, transcript, meeting recording, or meeting notes and asks to write a polished WeChat official-account article, event report, public communication draft, or to create/落一份 into a Feishu document. Covers source extraction, transcript-based synthesis, public fact-checking for organizations/people/projects, ASR/OCR correction, WeChat-style writing, and Feishu doc creation with verification.
---

# Write WeChat Article From Minutes

## Overview

Turn event materials such as posters, Feishu/Lark Minutes, meeting transcripts, and rough notes into a publishable WeChat official-account article, then optionally create a Feishu document and verify that the content actually landed.

Use existing Feishu and web skills as building blocks. This skill defines the end-to-end editorial workflow, fact discipline, document handoff, and verification harness.

## Required Skills And Tools

- Use `lark-minutes` for Minutes metadata and `lark-vc`/`vc +notes` for transcript and AI artifacts.
- Use `lark-doc` when creating, updating, or checking Feishu documents.
- Use `web-access` or available web search for public fact-checking. Prefer official sources and first-party pages.
- Use image viewing/OCR judgment for posters. Correct ASR/OCR mistakes using poster evidence and public sources.

When any referenced skill is used, read its `SKILL.md` and required references first.

## Success Criteria

- Event facts are extracted from the poster and Minutes: title, time, location, hosts, organizers, agenda, speaker names/titles, and key activity flow.
- Main claims come from the original transcript or poster. AI summary artifacts are supporting material only.
- Organization, person, project, and company names are checked against public sources when they affect the published text.
- ASR/OCR errors are corrected explicitly, such as `慧联` -> `汇联` when the poster/public sources support that correction.
- The article reads like a human-edited WeChat public-account article, not a meeting minutes dump.
- If the user asks to create a Feishu doc, the final doc URL is returned after a fetch/readback check confirms the real article text landed.

## Workflow

### 1. Establish Inputs And Acceptance

Identify the available materials:

- Poster or image path.
- Feishu/Lark Minutes URL or `minute_token`.
- Any requested outlet, tone, length, title style, or publishing constraints.
- Whether the user wants only draft text or also a Feishu document.

If the request is ambiguous but safe to assume, proceed with a default WeChat article:

- 1 headline.
- 800-1400 Chinese characters unless the material calls for more.
- Structure: lead -> event facts -> platform/context -> speaker highlights -> exchange/resource matching -> closing.
- End with a short "核验说明" only when useful for the user's review. Omit it from a final publication version if the user asks for clean copy.

### 2. Build The Evidence Harness

For a Minutes URL, extract the token from the final path segment:

```bash
lark-cli minutes minutes get --as user --params '{"minute_token":"TOKEN"}'
lark-cli vc +notes --as user --minute-tokens TOKEN --overwrite
```

Use the exported transcript path from `vc +notes`. Inspect it with narrow commands:

```bash
wc -l path/to/transcript.txt
sed -n '1,220p' path/to/transcript.txt
rg -n "主题|主办|承办|协办|嘉宾|AI|OPC|创业|资源|对接|交流" path/to/transcript.txt
```

Treat the transcript as the primary source for what was said. Treat poster text as the primary source for activity facts. Treat AI-generated summary/chapters as a map, not as a publishable source.

### 3. Cross-Check Public Facts

For every unit, person, project, or company that appears in the final article:

- Search public sources if the information is current or externally visible.
- Prefer official websites, university pages, government pages, company pages, or original announcements.
- Use authoritative media only when no official source is available, and note the lower confidence.
- Do not invent honorifics, rankings, titles, or institutional affiliations from a transcript alone.
- If a name/title cannot be verified, either keep it exactly as the poster states or add a review note such as "建议发布前由主办方确认".

Common corrections:

- Compare poster text against transcript output for homophones and ASR errors.
- Use the poster spelling for event names, organizations, agenda titles, and contact labels unless public sources prove otherwise.
- Avoid putting private phone numbers or personal contact details into the article unless the user explicitly wants the invitation content reproduced.

### 4. Draft The Article

Write with a public-account editorial voice:

- Lead with the event and its significance, not a generic slogan.
- Keep the structure clean and paragraphing brisk.
- Convert speeches into editorial takeaways; do not transcribe speaker remarks paragraph by paragraph.
- Use concrete facts: exact date, place, organizers, session names, speaker names, and interaction format.
- Preserve useful language from speakers only as short paraphrase or short quotes.
- Avoid obvious AI patterns such as repetitive `不是...而是...`, over-neat three-part slogans, inflated adjectives, and empty transitions.
- Do not overclaim results. Prefer "围绕...展开交流", "分享了...", "现场设置..." over "取得圆满成功" unless the material supports it.

Suggested structure:

```markdown
# 标题

导语：时间、地点、活动、主承协办、主题和现场目的。

## 平台/空间介绍
提炼承办方或园区的定位、服务逻辑、场景与资源。

## AI趋势和创业能力
提炼专家关于AI趋势、创业者能力、真实交付的观点。

## OPC社区运营和资源对接
提炼社区如何帮助创业者找到客户、订单、政策、资本和协作网络。

## 现场交流和下一步
写自由交流、展位体验、政企资源对接，以及后续平台承诺。

## 信息核验与发布前确认
仅供审稿时使用。
```

### 5. Create The Feishu Document When Requested

Read `lark-doc` first. Check the live CLI help because `lark-cli docs +create` flags can differ from older skill references:

```bash
lark-cli docs +create --help
lark-cli docs +update --help
lark-cli docs +fetch --help
```

Prefer Markdown for this article workflow because it maps well to WeChat editorial sections and current CLI support:

```bash
lark-cli docs +create \
  --title "TITLE" \
  --markdown "$(cat article.md)"
```

Do not trust `--markdown @article.md` unless a readback proves the file content was expanded. Some CLI versions treat `@file` literally for `--markdown`. If that happens, immediately overwrite:

```bash
lark-cli docs +update \
  --doc "DOC_URL" \
  --mode overwrite \
  --markdown "$(cat article.md)"
```

Use a review-friendly document shape:

- H1 headline.
- Opening quote/callout note if the doc is an editable draft.
- Activity facts table.
- H2 sections for the article body.
- Optional information-check section with source notes and publication risks.

### 6. Verify Before Final Reply

Always verify the handoff:

```bash
lark-cli docs +fetch --doc "DOC_URL"
```

Check:

- Returned title matches.
- Returned content length is plausible for the article, not a tiny placeholder.
- Key headings exist.
- The body does not only contain a literal filename such as `@article.md`.
- Known ASR/OCR corrections are present.

If verification fails, fix the document and fetch again before claiming completion.

Final reply should include:

- The Feishu doc URL when created.
- One concise verification sentence.
- Any remaining publication risk, such as unverified title or speaker name, if relevant.

## Quality Rules

- Use absolute dates if the user uses relative dates and there is any risk of confusion.
- Keep all names, organizations, titles, and project names consistent across headline, body, tables, and notes.
- State uncertainty plainly and early. Do not bury unverified claims in polished prose.
- Clean up local temporary draft files after successful doc verification unless they are useful deliverables requested by the user.
