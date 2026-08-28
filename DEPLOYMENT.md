# YLMS · Guía de Despliegue en Windows Server

Yazoo Laboratory Management System — Rones y Bebidas del Caribe
Versión: 2.0 · Iter 19 · Feb 2026

Este documento cubre la **instalación local en Windows Server** para la
presentación en Yazoo con datos persistentes en Microsoft SQL Server.

---

## 1. Prerrequisitos

En el servidor deben estar instalados (en este orden):

| Componente | Versión mínima | Notas |
|---|---|---|
| Windows Server | 2019 o superior | 8 GB RAM recomendado |
| **Python** | 3.11.x | 64-bit, marcar "Add to PATH" |
| **Node.js LTS** | 20.x | Con Yarn (`corepack enable`) |
| **Microsoft SQL Server** | 2019 Express o superior | Con SQL Server Authentication habilitado |
| **ODBC Driver 17 for SQL Server** | ≥ 17.10 | Obligatorio para `pyodbc` |
| Git | 2.40+ | Opcional (para pull de actualizaciones) |

### 1.1 Habilitar autenticación mixta en SQL Server
1. SQL Server Management Studio → Botón derecho sobre la instancia → Properties → Security.
2. Selecciona **SQL Server and Windows Authentication mode**.
3. Reinicia el servicio "SQL Server (MSSQLSERVER)".

### 1.2 Crear base de datos y usuario
```sql
CREATE DATABASE ylms_prod;
GO
CREATE LOGIN ylms_app WITH PASSWORD = 'CambiarEnProduccion!2026';
GO
USE ylms_prod;
CREATE USER ylms_app FOR LOGIN ylms_app;
EXEC sp_addrolemember 'db_owner', 'ylms_app';
GO
```

---

## 2. Estructura de carpetas recomendada

```
C:\YLMS\
├── app\             (código clonado del repositorio)
│   ├── backend\
│   ├── frontend\
│   └── DEPLOYMENT.md (este archivo)
├── logs\
└── data\            (uploads, firmas, PDFs)
```

Descomprime/copia el proyecto en `C:\YLMS\app`.

---

## 3. Backend · FastAPI

### 3.1 Crear entorno virtual
```powershell
cd C:\YLMS\app\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 3.2 Instalar dependencias
```powershell
pip install -r requirements.txt
# Extra para SQL Server:
pip install pyodbc
```

### 3.3 Configurar variables de entorno (`backend\.env`)
```ini
# --- Conexión a SQL Server ---
MONGO_URL=mssql+aioodbc://ylms_app:CambiarEnProduccion!2026@localhost/ylms_prod?driver=ODBC+Driver+17+for+SQL+Server
DB_NAME=ylms_prod

# --- JWT ---
JWT_SECRET=<generar-64-caracteres-aleatorios>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MIN=480

# --- Emergent Universal Key (LLM opcional) ---
EMERGENT_LLM_KEY=<tu-key-aqui>
```

Genera `JWT_SECRET`:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 3.4 Migrar / semilla inicial
```powershell
python -m server  # Iniciará y creará todas las colecciones/tablas
```

En la primera ejecución, el sistema crea automáticamente:
- Usuario admin: **admin@yazoo.com / Admin123!** (⚠️ cámbialo).
- Los 13 módulos ERP en `system_modules`.
- Catálogo de screens y roles.

### 3.5 Ejecutar como servicio Windows (recomendado)
Usa **NSSM** (Non-Sucking Service Manager):
```powershell
nssm install YLMS-Backend "C:\YLMS\app\backend\.venv\Scripts\python.exe" ^
             -m uvicorn server:app --host 0.0.0.0 --port 8001
nssm set    YLMS-Backend AppDirectory "C:\YLMS\app\backend"
nssm set    YLMS-Backend AppStdout    "C:\YLMS\logs\backend.log"
nssm set    YLMS-Backend AppStderr    "C:\YLMS\logs\backend.err.log"
nssm start  YLMS-Backend
```

Verifica: `curl http://localhost:8001/api/health` → `{"status":"ok"}`

---

## 4. Frontend · React 19

### 4.1 Instalar y compilar
```powershell
cd C:\YLMS\app\frontend
yarn install
```

### 4.2 Configurar variables (`frontend\.env`)
```ini
REACT_APP_BACKEND_URL=http://ylms-server.local:8001
# O la IP local del servidor, ej.:
# REACT_APP_BACKEND_URL=http://192.168.1.50:8001
```

### 4.3 Build de producción
```powershell
yarn build
```
Genera `frontend\build\` con todos los assets estáticos.

### 4.4 Servir el frontend
Opción A — **IIS** (recomendado en Windows Server):
1. Copia `frontend\build\` a `C:\inetpub\wwwroot\ylms\`.
2. Crea un sitio nuevo en IIS Manager apuntando a esa carpeta, puerto 80.
3. Agrega la regla de reescritura para SPA (crear `web.config` en la raíz):
```xml
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="SPA" stopProcessing="true">
          <match url=".*" />
          <conditions logicalGrouping="MatchAll">
            <add input="{REQUEST_FILENAME}" matchType="IsFile"    negate="true" />
            <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
          </conditions>
          <action type="Rewrite" url="/" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
```

Opción B — **serve** (rápido para demo):
```powershell
npm install -g serve
serve -s frontend\build -l 80
```

---

## 5. Cortafuegos y red

Abre los puertos:
- **80** (frontend) → todo el intranet.
- **8001** (backend API) → solo el frontend (o cualquier IP interna).
- **1433** (SQL Server) → solo `localhost` (backend).

```powershell
New-NetFirewallRule -DisplayName "YLMS Frontend" -Direction Inbound -LocalPort 80    -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "YLMS Backend"  -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
```

---

## 6. Post-instalación

### 6.1 Cambiar contraseña admin
1. Ingresa como `admin@yazoo.com` / `Admin123!`.
2. Ve a **Sistema → Usuarios**, edita el admin y cambia la contraseña.

### 6.2 Configurar firmas
Cada usuario debe subir su firma electrónica desde el ícono de la pluma
(header). Sin firma cargada, el sistema bloquea las operaciones (guardia
ISO 9001 / BPM).

### 6.3 Semilla de datos iniciales
Opcionalmente ejecuta:
```powershell
python scripts\seed_yazoo_data.py
```
Crea productos, tanques, proveedores, clientes y reactivos de demo.

### 6.4 Verificación de salud
```powershell
curl http://localhost:8001/api/health
curl http://localhost:8001/api/system/modules
```
Ambos deben responder 200 OK.

---

## 7. Backup y mantenimiento

- **BD**: SQL Server Agent → job diario `BACKUP DATABASE ylms_prod TO DISK`.
- **Firmas y adjuntos**: sincroniza `C:\YLMS\app\backend\data\` a un
  recurso de red o OneDrive Business.
- **Logs**: rota `C:\YLMS\logs\*.log` cada semana con `LogRotateWin` o
  tarea programada.

---

## 8. Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `pyodbc.InterfaceError` en boot | Falta ODBC Driver 17 | Instalar desde Microsoft |
| Frontend muestra "Sin conexión" al ir a producción | `REACT_APP_BACKEND_URL` apunta a `localhost` | Reconstruir con la IP correcta |
| `psycopg2` u otros errores raros | Estás usando la venv equivocada | `.venv\Scripts\Activate.ps1` |
| Login funciona pero no ves menús | Rol sin screens asignados | Sistema → Usuarios → editar screens |
| PDF vacío o corrupto | Falta ReportLab o `assets\yazoo-logo.png` | Reinstalar `pip install -r requirements.txt` |

---

## 9. Contacto

- Producto: **YLMS 2.0** · Yazoo Rones y Bebidas del Caribe
- Soporte técnico: `ti@yazoo.com` (interno)
- Credenciales de fábrica (cambiar tras instalación): `admin@yazoo.com / Admin123!`

Documento controlado por Ing. TI Yazoo · Rev. 01 · Feb 2026.
