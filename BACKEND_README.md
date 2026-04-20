# Film Archive 后端使用说明

本项目支持两种后端部署模式：**Supabase Edge Function**（生产推荐）和**本地 FastAPI**（开发调试）。

---

## 模式一：Supabase Edge Function（生产环境）

### 环境要求

- Supabase 项目（免费套餐即可）
- Supabase CLI（`npm install -g supabase`）

### 配置

`backend/api.js` 通过域名自动选择后端地址：

| 访问域名 | 自动使用的 API 地址 |
|---------|-------------------|
| `*.meoo.host` / `*.meoo.space` | `{origin}/sb-api/functions/v1/film-archive` |
| 其他（GitHub Pages 等） | `http://localhost:8000/api` |
| `localStorage.api_base_url` 有值 | 使用存储值（最高优先级） |

如需手动指定，在浏览器控制台执行：

```javascript
localStorage.setItem('api_base_url', 'https://xxx.supabase.co/functions/v1/film-archive')
location.reload()
```

### API 响应格式

所有 Edge Function 接口返回统一信封：

```json
// 成功
{ "data": { ... } }

// 失败
{ "error": "错误描述" }
```

### 认证说明

- 登录使用**邮箱 + 密码**，Token 从 `data.data.session.access_token` 中获取
- Token 无自动刷新端点，过期后前端自动清除 Session 并跳转登录页
- 退出登录会先调用 `POST /auth/logout` 通知服务端，失败也会清除本地 Token

### 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册（username, email, password） |
| POST | `/auth/login` | 登录（email, password） |
| POST | `/auth/logout` | 退出 |
| GET  | `/auth/me` | 当前用户信息 |
| GET  | `/rolls` | 胶卷列表 |
| POST | `/rolls` | 创建胶卷 |
| GET  | `/photos?roll_id=` | 照片列表（可按胶卷过滤） |
| POST | `/photos` | 添加照片 |
| PUT  | `/photos/{id}` | 更新照片 |
| DELETE | `/photos/{id}` | 删除照片 |
| POST | `/sync` | 批量上传胶卷和照片 |
| GET  | `/search?q=` | 全文搜索 |
| GET  | `/stats` | 统计概览 |

---

## 模式二：本地 FastAPI（开发调试）

### 快速启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 访问 API 文档

启动后打开：http://localhost:8000/docs

### Docker 启动（推荐）

```bash
# 一键启动前后端
docker-compose up -d

# 前端：http://localhost
# 后端 API：http://localhost/api
```

---

## 常见问题

### CORS 错误

检查后端 `.env` 中的 `CORS_ORIGINS` 是否包含前端地址，默认已包含 `null`（支持直接打开 HTML 文件）。

### Token 相关

| 现象 | 原因 | 解决 |
|------|------|------|
| 登录后所有请求 401 | localStorage 中 `access_token` 值为字符串 `"undefined"` | 清除 localStorage，重新登录 |
| 页面突然跳回登录页 | Token 过期（401），这是正常行为 | 重新登录即可 |
| 退出后仍显示已登录 | 清除缓存 | 强刷页面（Ctrl+Shift+R） |

清除本地认证数据：

```javascript
localStorage.removeItem('access_token')
localStorage.removeItem('refresh_token')
localStorage.removeItem('current_user')
location.reload()
```

### 切换后端地址

```javascript
// 切换到 Supabase
localStorage.setItem('api_base_url', 'https://your-project.supabase.co/functions/v1/film-archive')

// 切回本地开发
localStorage.setItem('api_base_url', 'http://localhost:8000/api')

// 恢复自动检测
localStorage.removeItem('api_base_url')

location.reload()
```
