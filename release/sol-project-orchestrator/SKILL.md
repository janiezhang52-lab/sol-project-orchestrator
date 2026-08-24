---
name: sol-project-orchestrator
description: 当用户以“立项：”提交非空目标，或在同一 Sol 项目中精确发送“去执行”“接受产品”“需要修订”“拒绝产品”“继续核对”“停止”时使用。用一个本地 SQLite driver 唯一编排四个可见任务、真实执行、独立验收、技术收口和最终产品决定。
---

# Sol 项目总控 MVP

你只是 Host 适配器。流程、去重、恢复和唯一下一动作只由
`scripts/sol_driver.py advance` 与项目外的唯一 SQLite 账本决定。

## 产品边界

- 仅支持一个保存项目中的 fresh A0；固定四个任务：00 总控、01 执行、02 验收、03 收口。
- 不联网、不下载、不装依赖、不执行 Git 命令、不修改 `.git/**`。
- driver 在 `$CODEX_HOME/state/sol-project-orchestrator/v1/` 保存控制账本；`CODEX_HOME` 未设置或不是绝对路径时使用 `~/.codex/state/sol-project-orchestrator/v1/`。它不在项目内创建 `.sol/`，也不修改项目里已有的 `.sol` 内容。
- 外置账本只用于崩溃恢复与防重放，不是防篡改或身份认证边界；拥有同一用户文件权限的本地进程仍能改它，`validate` 只检查有限结构与哈希不变量。
- Host 回执属于 caller-supplied observation，不是本地 driver 独立认证的 Host 真相。
- `read_thread` 不是完整工具账本。技术收口不等于用户接受产品。

## 绝对规则

- 只调用 driver 的 `advance` 与只读 `validate`；不要读写 SQLite，不要自行修状态。
- 每次只执行 `next_action` 指定的一条 Host 动作；原样使用 `tool` 和 `args`。
- 不补参数、不换工具、不猜阶段、不按标题选角色、不重发 mutation。
- 原始 Host 结果必须完整回传；object/array 原样传，JSON 文本字符串也原样传。driver 只会严格解包一层；不得摘要、重构或自报 success/fresh。
- driver 返回 `WAIT_USER`、`TERMINAL` 或错误后立即停止自动循环。
- 用户不需要复制 ID、JSON、回执、游标或内部命令。

## 输入

只接受以下整条消息：

- `立项：<非空目标>`
- `去执行`
- `接受产品`
- `需要修订`
- `拒绝产品`
- `NEEDS_INPUT` 后的 `继续核对`
- `NEEDS_INPUT` 后的 `停止`

`立项：` 后的文字去除首尾空白后作为冻结目标。其他命令只允许 Host transport 附加的一个末尾 LF 或 CRLF；先仅去掉这一个换行，再精确匹配固定词。不得 trim 空格，不得接受裸 CR、多重换行或正文内换行。

## 当前任务与项目绑定

在任何 INIT 或 USER_INPUT 前先完成只读绑定：

1. 用 `mcp__node_repl__js` 仅执行一次以下固定代码，`timeout_ms=30000`：

   `{ nodeRepl.write(typeof nodeRepl.requestMeta?.threadId === "string" ? nodeRepl.requestMeta.threadId : ""); nodeRepl.write("\n"); nodeRepl.write(typeof nodeRepl.requestMeta?.["x-codex-turn-metadata"]?.thread_id === "string" ? nodeRepl.requestMeta["x-codex-turn-metadata"].thread_id : ""); }`

2. 返回必须恰为两个非空且完全一致的 ID。不要输出整个 `requestMeta`，不要从标题、cwd、active 或最近任务猜 ID。
3. 调用 `list_projects` 与 `list_threads(limit=50)`。这两个只读工具若返回 JSON 文本字符串，只严格解析一层；解析失败即停止。当前 ID 必须唯一可见；其非空 `projectId`、`hostId=local`、cwd 必须与唯一保存项目的 exact root 一致；unavailable host/source 必须为空。
4. 账本是否存在只能由下文同一 root/projectId 的 `validate` 判定，不得扫描状态目录。初次立项且账本不存在时，本轮可见的同项目 Codex 任务必须只有当前任务，才能提交 `fresh_asserted=true`。账本已存在时只做身份绑定，不重新声称 fresh。
5. 任一值缺失、冲突或工具不可用：输出 `PROJECT_BINDING_FAILED` 的人话说明并停止；不得创建 ledger 或 Host 任务。

## 调用 driver

先用 `codex_app__load_workspace_dependencies` 取得 bundled Python。driver 路径固定为本 Skill 根下
`scripts/sol_driver.py`。使用 bundled Python、`-X utf8 -B`、绝对项目根调用：

`<bundled-python> -X utf8 -B <Skill根>/scripts/sol_driver.py advance --project-root <root> --project-id <projectId> --request <absolute-json-path>`

调用 `validate` 时也必须使用同一绑定身份：

`<bundled-python> -X utf8 -B <Skill根>/scripts/sol_driver.py validate --project-root <root> --project-id <projectId>`

- `advance` 任意非零退出，或 `validate` 除下述唯一例外外任意非零退出，立即失败关闭并停止，不得调用 Host。
- 唯一例外：`validate` 的 Host outer `exit_code` 为 `1` 或 `2`，且 `stdout` 严格解析后的对象恰为 `{"valid":false,"errors":["ledger:not_found"]}`；这只表示外置账本不存在，可以继续提交首次 `INIT`。outer `1` 只兼容 Windows Host 对 child `2` 的归一化，不放宽任何其他非零结果。
- `stdout` 不能解析为单个严格 JSON 对象（即非严格 JSON）时立即失败关闭并停止。
- 严格解析后的 JSON 对象任意字符串字段含 `U+FFFD` 时立即失败关闭并停止，不得猜测或修复乱码。
- 存在待回填的 `HOST_MUTATE` 或 `HOST_OBSERVE` 时不得提交 `TICK`；必须先执行或回填当前唯一动作。

`validate` 只返回 `ledger:not_found` 才表示外置账本不存在；旧项目内账本、双位置、身份或路径冲突都必须停止，不得迁移、复制、合并、删除或回退到项目内。

请求文件只能放在操作系统临时目录，必须是 UTF-8 无 BOM 的单个严格 JSON；不要把用户目标插入 shell 代码。调用结束后立即删除临时请求文件。不得在项目内另建 request、cursor、receipt 或状态文件。

首次立项提交：

```json
{"schema":"sol-mvp-request-v1","kind":"INIT","objective":"<冻结目标>","project":{"project_id":"<projectId>","host_id":"local","root":"<绝对根>","sol_thread_id":"<当前ID>","is_git_repository":false,"fresh_asserted":true}}
```

`is_git_repository` 必须使用保存项目的真实布尔值，示例中的 `false` 不是默认值。

后续输入先提交 `TICK`。若 driver 已在处理中，就继续它给出的动作；只有当返回的 `WAIT_USER` 正在等待本条语义输入时，才提交：

```json
{"schema":"sol-mvp-request-v1","kind":"USER_INPUT","text":"<用户整条原文>","source_thread_id":"<当前ID>"}
```

`TICK` 为：`{"schema":"sol-mvp-request-v1","kind":"TICK"}`。

## 唯一执行循环

每次解析 driver 响应中的唯一 `next_action`：

1. `HOST_MUTATE`
   - 只允许 `create_thread`、`set_thread_title`、`send_message_to_thread`。
   - 精确调用一次；即使返回不确定也绝不再次调用该 mutation。
2. `HOST_OBSERVE`
   - 只允许 `list_threads`、`wait_threads`、`read_thread`。
   - 精确调用一次。等待超时也是原始结果，不是重发 mutation 的理由。
3. Host 返回可序列化结果后，立即提交：

```json
{"schema":"sol-mvp-request-v1","kind":"OBSERVATION","action_id":"<next_action.action_id>","observation_id":"<next_action.observation_id>","tool":"<next_action.tool>","result":<原始Host JSON>}
```

4. Host 工具抛错且没有 JSON 结果时，提交 `TOOL_FAILURE`，不得用 `TICK` 冒充观察：

```json
{"schema":"sol-mvp-request-v1","kind":"TOOL_FAILURE","action_id":"<next_action.action_id>","observation_id":"<next_action.observation_id>","tool":"<next_action.tool>","error":"<实际简短错误>"}
```

5. 再次调用 `advance`，直到 `WAIT_USER` 或 `TERMINAL`。持续工作时每 60 秒内给用户一条短进度，不泄漏内部 JSON/ID。

## 停止与输出

- `WAIT_USER`：停止工具循环，只把 `user_prompt` 转成简短人话告诉用户。
- `TERMINAL`：停止并报告 `user_prompt`；不得自动开启修订轮。
- `NEEDS_INPUT`：mutation 不会自动重发；只接受 driver 指定的 `继续核对` 或 `停止`。
- 成功创建任务后，在本轮 final 末尾按平台要求逐行输出对应的裸 `::created-thread` directive。
- 除平台 directive 外，不向用户回显 ledger、action ID、thread ID、raw JSON 或内部错误栈。
