# Procesador de Pedidos de Venta

Una aplicación web Flask para convertir archivos Excel de pedidos de venta al formato de plantilla requerido.

## 🚀 Deploy en Render

### Opción 1: Deploy Automático con GitHub

1. **Subir código a GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Pedidos processor"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
   git push -u origin main
   ```

2. **Conectar con Render:**
   - Ve a [render.com](https://render.com)
   - Conecta tu cuenta GitHub
   - Selecciona "New Web Service"
   - Conecta tu repositorio
   - Render detectará automáticamente el `render.yaml`

### Opción 2: Deploy Manual con Docker

1. **Construir imagen localmente:**
   ```bash
   docker build -t pedidos-processor .
   ```

2. **Probar localmente:**
   ```bash
   docker run -p 5000:5000 -e PORT=5000 pedidos-processor
   ```

3. **Deploy directo a Render:**
   - Usa el archivo `render.yaml` incluido
   - Render construirá automáticamente desde Dockerfile

## 🐳 Desarrollo Local con Docker

### Desarrollo rápido:
```bash
docker-compose up --build
```

### Reconstruir tras cambios:
```bash
docker-compose up --build --force-recreate
```

## 📁 Estructura del Proyecto

```
.
├── app.py              # Aplicación Flask principal
├── templates/          # Plantillas HTML
│   ├── index.html     # Página principal
│   └── preview.html   # Vista previa de mapeo
├── uploads/           # Archivos subidos (temporal)
├── outputs/           # Archivos procesados
├── Dockerfile         # Configuración Docker
├── docker-compose.yml # Desarrollo local
├── requirements.txt   # Dependencias Python
├── render.yaml       # Configuración Render
└── .dockerignore     # Exclusiones Docker
```

## ⚙️ Variables de Entorno

- `PORT`: Puerto del servidor (automático en Render)
- `FLASK_ENV`: Entorno de Flask (development/production)
- `SECRET_KEY`: Clave secreta (generada automáticamente en Render)

## 📊 Funcionalidades

- ✅ Subida de archivos Excel (.xlsx, .xls)
- ✅ Procesamiento automático de pedidos de venta
- ✅ Mapeo inteligente a formato plantilla
- ✅ Descarga automática de archivo CSV procesado
- ✅ Interfaz moderna estilo shadcn
- ✅ Dockerizado y listo para producción
- ✅ Health checks incluidos

## 🔧 Solución de Problemas

### Error de build en Render:
```bash
# Verificar que todos los archivos están presentes
ls -la

# Probar build local
docker build -t test .
```

### Error de dependencias:
```bash
# Regenerar requirements.txt
pip freeze > requirements.txt
```

### Error de permisos:
- Render usa usuario no-root por seguridad
- Verificar que las carpetas uploads/ y outputs/ son escribibles

## 📞 Soporte

Si tienes problemas con el deploy:
1. Verifica que el repositorio GitHub esté público
2. Revisa los logs en Render Dashboard
3. Confirma que el `render.yaml` esté en la raíz del proyecto