# Framework Adapters

本文件定义如何从框架源码建立候选路由，以及什么证据可以升级为当前页面事实。所有框架都服从 route union、current-run provenance 和 evidence gate。

## 通用路由并集

按以下来源合并，不能任选其一：

1. 当前服务实际 sitemap；
2. `--routes-file` 显式映射；
3. 框架公开路由；
4. 已注册内容集合。

去重后保留全部 `sources`。已注册但未进入 sitemap 的内容仍是目标路由；存在内容文件但不在 registry 的条目归为 `unregistered`，不得假设它可访问。

来源冲突时：

- `index_intent` 以显式 routes file 为最高优先级；
- sitemap 提供具体可访问候选，但不能覆盖显式 `noindex`；
- 框架源码提供路由形状，动态 token 不能凭文件名发明 slug；
- registry 提供具体内容实体和 slug；
- 无法解决的冲突写 coverage gap 和 `Unknown`。

## 统一分类

默认不做 on-page 评分，但仍要验证/分类：

- `api`：API、RPC、webhook、feed 数据端点；
- `auth`：登录、注册、OAuth callback、密码重置；
- `admin`：管理、内部工具、账户后台；
- `error`：404/500/error/not-found；
- `redirect`：纯跳转入口；
- `metadata`：robots、sitemap、manifest、图标等；
- `unregistered`：内容存在但没有公开 registry/route 证据。

路由前缀只能产生候选分类；middleware、redirect 配置和当前 HTTP 响应用于确认。

## Next.js

### 路由识别

同时识别根目录与 `src/` 下的 App Router/Pages Router：

- `app/**/page.*`、`src/app/**/page.*`；
- `pages/**/*.*`、`src/pages/**/*.*`，排除 `_app`、`_document`、`_error` 和 API；
- metadata routes：`app|src/app/robots.*`、`sitemap.*`、`manifest.*`、`opengraph-image.*`、`twitter-image.*`；
- route handlers 只按实际职责分类，不当作页面。

App Router 转 URL 时：

- `(group)` 和 `(.)`/`(..)`/`(...)` interception 语法不成为 URL segment；
- `_private` 目录不形成公开 route；
- `[slug]`、`[...slug]`、`[[...slug]]` 只保留 route pattern，具体 URL 必须来自 sitemap、routes file、`generateStaticParams` 可确定值或 registry；
- pattern 只有在受信任的 sitemap/routes file/registry 具体路由与其匹配时才可标 `classified`，并记录 `matched_routes`；没有具体实体证据时保留 coverage gap；
- locale segment 要与 middleware/i18n/registry 支持范围交叉验证，不能把任意 `/xx/` 当有效语言；
- parallel route `@slot` 不单独生成 URL。

### Metadata 继承

App Router metadata 沿 root layout、嵌套 layout、page 合并；更深 segment 的字段覆盖父级，未设置字段可以继承。审计必须解析或通过当前 HTML 验证继承结果，不能只因 `page.*` 没有 `metadata` 就报告缺失。

动态 metadata 只有在具体参数和数据返回已知时才能确认。`generateMetadata`、shared metadata helper、`metadataBase`、title template 和 locale layout 都是候选来源。

Next.js 官方规则：[generateMetadata](https://nextjs.org/docs/app/api-reference/functions/generate-metadata)。

### Client Component

`"use client"` 表示组件边界，不表示首次响应一定没有 HTML。Client Component 可以参与服务器生成初始 HTML；metadata 也可能由 layout/page 合并得到。只有当前 HTTP 响应确实缺少主要内容，才能报告 rendered-content 问题。

Next.js 官方术语：[Client Component](https://nextjs.org/docs/app/glossary)。

### 当前证据

- 永远排除既有 `.next`、`.open-next`、standalone、cache 和历史 output。
- 获准运行时：记录 commit 和开始时间，成功完成本轮 build，启动对应服务，再用 `--base-url` 取 HTTP 响应。
- build 失败或服务不可达写 `Unknown`/coverage gap，不能回退解析旧 `.next`。
- 若存在动态集合，在 localhost 请求明显不存在且不会碰撞的 slug；200 且输出空白/占位/近重复实体时生成 soft-404 证据。
- 解析当前 `robots.txt` 的 `User-agent: *` 规则；全站封锁与最长匹配的路由级 Allow/Disallow 分开判断。

## Nuxt

- 从 `pages/`、`app/pages/`、router 配置和内容 registry 建立候选路由；`[param]` 与 catch-all 仍需具体实体来源。
- `useHead`、`useSeoMeta`、layout/app head 与 page head 可能合并；源码缺字段只能是 Candidate。
- SSR/SSG 项目优先通过本轮本地服务；纯静态输出可使用显式 `--rendered-root`。
- Nitro/server/API routes 分类为 API，不做页面评分。

## Astro

- `src/pages` 文件路由、`getStaticPaths` 结果、content collections 和显式 redirects 共同建立 route union。
- layout/frontmatter 可能提供继承 metadata；page 文件缺 head 不等于运行时缺失。
- 静态构建只扫描显式、本轮生成的 `--rendered-root`；SSR adapter 使用 `--base-url`。
- endpoints 与页面分开分类。

## SvelteKit

- `src/routes/**/+page.*` 是页面；`+server.*` 是 API；`+error.*` 是错误页。
- route group 不进入 URL，`[param]`/rest/optional param 需要具体来源。
- `+layout` load/head 结果可能由父级提供，最终以本轮响应为准。
- prerender 结果只能通过 current-run `--rendered-root` 使用。

## Gatsby

- `src/pages`、File System Route API、`createPages` 和数据 registry 合并。
- GraphQL 数据驱动页面必须从创建逻辑/registry 得到具体 path；模板文件本身不是 URL。
- 只读取本轮 `public/`，且必须作为显式 `--rendered-root` 传入。

## React/Vite 与其他 SPA

- 从显式 router 配置、sitemap 和 routes file 建立路由，不能从组件文件数量推断 URL。
- `ReactDOM`、router 或 client directive 只说明实现方式，不证明搜索引擎收到空 HTML。
- 有 SSR 服务时使用 `--base-url`；prerender/SSG 时使用 current-run `--rendered-root`；两者都没有时保持 source-only Candidate/Unknown。

## 传统服务端与静态站

- Rails/Laravel/Django/Express 等从公开 route 表、模板映射、sitemap 和内容 registry 建立并集；认证/API route 另行分类。
- WordPress 等 CMS 的源码目录不能代表当前文章清单；需要 sitemap、导出或当前 HTTP。
- 手写静态站可从 `.html` 输出映射 URL，但只有本轮生成且显式传入的 rendered root 才是页面证据。

## 源码 allowlist 与硬排除

只扫描框架公开源码、配置和已注册内容：`src/`、`app/`、`pages/`、`routes/`、`content/`、`posts/`、必要的 `public/` SEO 文件及根配置。项目实际结构可缩小 allowlist，不能扩大为整个磁盘。

无条件排除：

- `.next`、`.open-next`、`dist`、`build`、`out`、`output`、standalone、cache；
- 报告目录、`.source`、Agent/AI 配置和内部规划文档；
- `.env*`、`.dev.vars`、secret、日志、数据库；
- uploads、用户输入、导入原件和其他原始数据；
- 扫描器自身输出。

路径排除在读取前执行；内容目录只读取 registry 确认的文件，未注册文件只保留安全的库存分类；symlink 或 resolve 后越出 root 的路径不得进入证据。`--exclude` 只能增加排除项，不能解除硬排除。
