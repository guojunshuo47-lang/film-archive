# Changelog

所有版本的更新记录都在这里。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)

---

## [Unreleased]

### Added
- 正在开发中的功能...

---

## [2.2.0] - 2026-04-17

### Added
- 手机端响应式适配：新增横向滚动移动导航栏（header 下方）
- 桌面侧边栏在手机上自动隐藏
- Header 按钮手机端只显示图标，桌面端显示文字
- 统计卡片手机端改为 2 列布局

### Changed
- Header 和 main 区域 padding 适配小屏幕（`px-4 md:px-8`）
- 表单行在手机上纵向堆叠，标签自适应宽度
- 照片概览控件支持换行，胶卷选择器手机端全宽
- 图片网格在手机上使用更小的最小宽度（130–140px）
- Section 面板 padding 手机端缩减（`p-4 md:p-6`）

---

## [2.1.0] - 2026-04-17

### Added
- 明暗主题切换按钮（Header 右侧月亮/太阳图标，主题持久化至 localStorage）
- 完整深色模式（`[data-theme="dark"]` CSS 变量组）

### Changed
- UI 风格全面改版为 Anthropic 设计语言：Inter 字体、珊瑚色 accent（#D97757）、简洁白底
- 替换中文毛笔字体（Ma Shan Zheng、ZCOOL XiaoWei）为 Inter + Noto Sans SC
- 主色调由暖米色改为 `#FAF9F7`，深色模式为 `#0F0F0F`
- 所有交互状态（焦点环、hover 边框、批量选择、心形收藏、状态点）统一使用珊瑚色
- 主要操作按钮改为填充式珊瑚色样式（btn-primary）
- 胶片盒卡片默认渐变改为深灰炭色 + 珊瑚色顶部色条
- Modal 背景新增 `blur(4px)` 效果

---

## [2.0.0] - 2026-04-12

### Changed
- 全面升级 UI 为第一版 film manager (film manager(7).html)
- 优化整体交互体验

---

## [1.3.0] - 2026-04-10

### Added
- 添加 EXIF 识别功能
- 添加分组展示功能
- 添加入门教学引导

### Fixed
- 优化交互体验

---

## [1.0.0] - 2026-04-09

### Added
- 初始版本发布
- 基础胶片管理功能
- GitHub Pages 部署支持

---

[Unreleased]: https://github.com/guojunshuo47-lang/film-archive/compare/v2.2.0...HEAD
[2.2.0]: https://github.com/guojunshuo47-lang/film-archive/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/guojunshuo47-lang/film-archive/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/guojunshuo47-lang/film-archive/compare/v1.3.0...v2.0.0
[1.3.0]: https://github.com/guojunshuo47-lang/film-archive/compare/v1.0.0...v1.3.0
[1.0.0]: https://github.com/guojunshuo47-lang/film-archive/releases/tag/v1.0.0
