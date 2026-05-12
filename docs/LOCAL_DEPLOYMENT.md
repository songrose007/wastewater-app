# 本地部署说明

## Ubuntu 24.04

```bash
chmod +x scripts/setup_ubuntu.sh scripts/dev_backend.sh scripts/dev_frontend.sh
./scripts/setup_ubuntu.sh
```

启动两个终端：

```bash
./scripts/dev_backend.sh
```

```bash
./scripts/dev_frontend.sh
```

访问：

```text
http://localhost:5173
```

后端接口文档：

```text
http://localhost:8000/docs
```

## Windows PowerShell

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
```

启动后端：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8000 --reload
```

启动前端：

```powershell
cd frontend
npm run dev
```

访问：

```text
http://localhost:5173
```

## 验证

```bash
./scripts/verify_local.sh
```

如果只验证前端：

```bash
cd frontend
npm run build
```

如果只验证后端：

```bash
cd backend
pytest tests/ -v
```
