# Film Archive 后端使用说明

## 快速开始

### 1. 启动后端服务

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 访问 API 文档

打开浏览器访问: http://localhost:8000/docs

### 3. 前端连接

前端默认连接 `http://localhost:8000/api`，确保后端在这个地址运行。

如果后端地址不同，可以在浏览器控制台设置:
```javascript
localStorage.setItem('api_base_url', 'http://your-server:8000/api')
location.reload()
```

## 常见问题

### CORS 错误

如果出现 "CORS policy" 错误，检查:
1. 后端 `.env` 中的 `CORS_ORIGINS` 是否包含前端地址
2. 默认已包含 `null` 以支持直接打开 HTML 文件

### 连接失败

1. 确保后端正在运行 (`uvicorn app.main:app --reload`)
2. 检查防火墙是否允许 8000 端口
3. 确认前端 `API_BASE_URL` 配置正确

## Docker 启动（推荐）

```bash
# 一键启动前后端
docker-compose up -d

# 访问前端 http://localhost
# 访问后端 API http://localhost/api
```
