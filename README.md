# Workbench Shell（统一公网工作台）

一个轻量的门户：读 `manifest.json` 动态渲染模块卡片，把分散开发的内容模块（静态工具 / 后端服务 / 文档）统一到一个公网入口。**完全公开、无登录。**

## 目录结构
```
workbench/
├── app.py              # Flask Shell：门户页 + /api/manifest + /modules 静态服务
├── manifest.json       # 模块注册表（新增模块只改这里 + modules/）
├── requirements.txt    # Flask
├── runtime.txt         # 3.11.9（Railway 运行环境）
├── railway.json        # Railway 部署配置（NIXPACKS + python app.py）
├── templates/
│   └── index.html      # 门户首页（暗色 UI，按 manifest 渲染卡片）
├── modules/            # 静态模块放这里，每个模块一个子文件夹
│   └── welcome/        # 示例：使用说明
└── static/             # Shell 自身静态资源（暂未用）
```

## 模块类型
- `static`：纯前端 HTML/JS 工具，放进 `modules/<id>/`，Shell 直接服务（`/modules/<id>/index.html`）。
- `iframe`：已有的后端服务（如 Railway 上的 Flask），用 iframe 嵌进来，原服务不动。
- `link`：第三方页面 / 文档入口，点击新标签页打开。

## 已集成模块
- **人力资本战略工作室**（`modules/hcss/`）：含战略目标分析器、能力矩阵、HR 体系、管理方格测评。
  - 管理方格测评支持三层模式：① 个人自测（零后端）；② 会后复查（轻后端 + 专属 token/二维码）；③ 团队汇总（可选姓名/部门 + 主持人口令看分布）。

## 本地运行（自测）
```bash
pip install -r requirements.txt
python app.py
# 打开 http://localhost:8080
```

## 部署到 Railway（公网）
方式 A — 命令行：
```bash
railway login
railway link        # 关联本目录为项目
railway up          # 部署，得到公网 URL
```
方式 B — 接 GitHub：把本目录推到仓库，Railway 关联后自动构建（`runtime.txt` + `railway.json` 已配好）。

部署后访问 Railway 给的公网 URL 即可；完全公开，无需任何登录。

## 新增模块（用整合 Skill）
开发完一个模块后，运行整合 Skill `workbench-integrator`（或在工作台根目录直接跑它的脚本）：

```bash
# 静态模块：把 ./mycalc 文件夹接入
python <skills>/workbench-integrator/integrate_module.py \
  --root . --id mycalc --title "我的计算器" --type static \
  --source ./mycalc --desc "离线计算器" --tags 工具,前端

# 已有后端服务：iframe 嵌入
python <skills>/workbench-integrator/integrate_module.py \
  --root . --id apisvc --title "API 服务" --type iframe \
  --url https://xxx.railway.app --tags 服务

# 外链 / 文档
python <skills>/workbench-integrator/integrate_module.py \
  --root . --id docs --title "文档中心" --type link \
  --url https://example.com --tags 文档
```
脚本会复制文件（静态类）并更新 `manifest.json`，**幂等**——相同 id 重复运行只更新不重复添加。
完成后重新部署（`railway up` 或推送 Git），首页就会出现新卡片。

## 设计要点
- **壳稳定、模块随到随接**：先部署空白 Shell（含 welcome 示例），模块从不同时候开发、逐个接入。
- **公网单入口**：所有模块共用一个 Railway URL，不用为每个工具单独部署。
- **迁移现有内容**：静态工具直接丢 `modules/`；Railway 后端服务用 iframe 接；Skill 转成展示页或文档入口。

## 模块：管理方格扫码测评（quiz）
自带后端（Flask 路由 + SQLite），无需问卷星。流程：
1. 投屏/发群 `modules/quiz/index.html` 的二维码 → 手机扫码即答。
2. 提交后生成 `lookup.html?token=xxx` 专属结果页 + 结果二维码，本人扫码即看，无需微信授权。
3. 主持人用口令（`QUIZ_HOST_PASSCODE`，默认 `hcss2026`，可环境变量覆盖）进 `host.html` 看实时汇总，手机/电脑通用，可导出 CSV。
- 算分逻辑：`quiz_core.py`（与 `modules/hcss/assets/js/grid-core.js` 算法逐字段对齐）。
- 存储：`data/quiz.db`（运行时生成，首次访问自动建表；Railway 免费版为临时盘，重启会清空，活动前清空重来即可）。

