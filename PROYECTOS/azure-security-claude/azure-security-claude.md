# Guía de Configuración: Analizador de Seguridad Azure + Claude

> **Objetivo:** Configurar un proyecto que recoge datos de seguridad de una VM en Azure y los analiza automáticamente con Claude AI.

---

## Requisitos previos

- Cuenta de Azure activa con una VM creada
- Python 3.9 o superior instalado
- Azure CLI instalado ([descargar aquí](https://learn.microsoft.com/es-es/cli/azure/install-azure-cli))
- API Key de Anthropic ([obtener aquí](https://console.anthropic.com))

---

## Paso 1 — Instalar Azure CLI y hacer login

Abre una terminal y ejecuta:

```bash
az login
```

> 📸 **CAPTURA AQUÍ:** Se abrirá el navegador para autenticarte con tu cuenta de Microsoft Azure. Haz una captura de la pantalla de login exitoso en el portal.

Una vez autenticado, verifica que puedes ver tu suscripción:

```bash
az account show
```

> 📸 **CAPTURA AQUÍ:** La terminal debe mostrar el JSON con tu suscripción activa. Copia el valor de `"id"` — ese es tu `SUBSCRIPTION_ID`.

---

## Paso 2 — Crear el Service Principal en Azure

El Service Principal es una identidad de aplicación que permite al script leer datos de tu VM sin usar tus credenciales personales.

```bash
az ad sp create-for-rbac \
  --name "claude-security-analyzer" \
  --role "Security Reader" \
  --scopes /subscriptions/<TU_SUBSCRIPTION_ID>
```

Sustituye `<TU_SUBSCRIPTION_ID>` por el valor obtenido en el paso anterior.

> 📸 **CAPTURA AQUÍ:** La terminal mostrará un JSON con las credenciales. **Guárdalo en un lugar seguro**, lo necesitarás en el paso 4. El JSON tiene esta forma:

```json
{
  "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "displayName": "claude-security-analyzer",
  "password": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

| Campo del JSON | Dónde usarlo en el script |
|----------------|--------------------------|
| `appId`       | `CLIENT_ID`             |
| `password`    | `CLIENT_SECRET`         |
| `tenant`      | `TENANT_ID`             |

---

## Paso 3 — Obtener los datos de tu VM

Ve al [Portal de Azure](https://portal.azure.com) y navega a tu máquina virtual.

> 📸 **CAPTURA AQUÍ:** Página principal de tu VM en el portal. Necesitas anotar:
> - **Nombre de la VM** (arriba del todo)
> - **Grupo de recursos** (campo "Resource group")

También puedes obtenerlos por terminal:

```bash
az vm list --output table
```

> 📸 **CAPTURA AQUÍ:** La tabla con todas tus VMs, donde se ven el nombre y el resource group.

---

## Paso 4 — Configurar el proyecto

### 4.1 Crea una carpeta para el proyecto

```bash
mkdir azure-security-claude
cd azure-security-claude
```

### 4.2 Instala las dependencias de Python

```bash
pip install anthropic azure-identity azure-mgmt-compute \
            azure-mgmt-security azure-mgmt-network
```

> 📸 **CAPTURA AQUÍ:** La terminal instalando los paquetes correctamente (verás "Successfully installed...").

### 4.3 Crea el archivo `collect.py`

Crea un archivo llamado `collect.py` y rellena las variables de la cabecera con tus datos:

```python
# ── Credenciales (edita estas líneas) ─────────────────────
SUBSCRIPTION_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"   # az account show → id
RESOURCE_GROUP  = "mi-resource-group"                       # nombre del resource group
VM_NAME         = "mi-vm"                                   # nombre de la VM
TENANT_ID       = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"   # del JSON del paso 2 → tenant
CLIENT_ID       = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"   # del JSON del paso 2 → appId
CLIENT_SECRET   = "tu-client-secret"                       # del JSON del paso 2 → password
```

> 📸 **CAPTURA AQUÍ:** El archivo `collect.py` abierto en tu editor con las variables ya rellenas (puedes tapar el CLIENT_SECRET por seguridad).

### 4.4 Crea el archivo `analyze.py`

Crea un archivo llamado `analyze.py` y añade tu API key de Anthropic:

```python
ANTHROPIC_API_KEY = "sk-ant-api03-..."   # tu key de console.anthropic.com
```

> 📸 **CAPTURA AQUÍ:** La sección de API keys en [console.anthropic.com](https://console.anthropic.com) donde copias tu key.

---

## Paso 5 — Verificar permisos del Service Principal

Antes de lanzar el script, verifica que el Service Principal tiene acceso a Security Center. En el portal de Azure:

1. Ve a tu **Subscription** → **Access control (IAM)**
2. Busca "claude-security-analyzer" en la lista de asignaciones de roles

> 📸 **CAPTURA AQUÍ:** La pantalla IAM mostrando el rol "Security Reader" asignado a "claude-security-analyzer".

Si necesitas más datos de seguridad, puedes añadir también el rol `Reader`:

```bash
az role assignment create \
  --assignee <APP_ID> \
  --role "Reader" \
  --scope /subscriptions/<SUBSCRIPTION_ID>
```

---

## Paso 6 — Ejecutar la recolección de datos

```bash
python collect.py
```

> 📸 **CAPTURA AQUÍ:** La terminal mostrando el resumen de datos recolectados:
```
🔍 Recopilando datos de la VM...
✅ Datos guardados en: vm_data_mi-vm.json
   • Extensiones:      3
   • Discos:           2
   • IPs públicas:     1
   • Reglas NSG:       5
   • Alertas:          2
```

Verifica que se ha creado el archivo JSON:

```bash
cat vm_data_mi-vm.json
```

> 📸 **CAPTURA AQUÍ:** El contenido del JSON con los datos de tu VM (puedes recortar si es muy largo).

---

## Paso 7 — Ejecutar el análisis con Claude

```bash
python analyze.py
```

El script detectará automáticamente el JSON más reciente y lo enviará a Claude para su análisis.

> 📸 **CAPTURA AQUÍ:** La terminal mostrando el informe completo generado por Claude, con las vulnerabilidades, alertas y plan de acción.

Al finalizar verás:

```
✅ Informe guardado en: security_report_mi-vm.md
```

> 📸 **CAPTURA AQUÍ:** El archivo `security_report_mi-vm.md` abierto — muestra el informe completo con secciones como "Vulnerabilidades críticas", "Análisis de red" y "Plan de acción".

---

## 🔄 Flujo completo resumido

```
collect.py  →  vm_data_<nombre>.json  →  analyze.py  →  security_report_<nombre>.md
  (Azure)         (datos crudos)         (Claude AI)       (informe final)
```

Puedes repetir el proceso cuando quieras. El JSON queda guardado por si necesitas re-analizar sin volver a llamar a Azure.

---

## 🛠️ Solución de problemas frecuentes

### Error: `AuthenticationError` al ejecutar collect.py

Verifica que las credenciales en la cabecera del script son correctas. El `CLIENT_SECRET` expira — puedes regenerarlo con:

```bash
az ad sp credential reset --name "claude-security-analyzer"
```

### Error: `ResourceNotFoundError` en el NSG

El Service Principal necesita permiso `Reader` además de `Security Reader`. Añádelo con el comando del Paso 5.

### Error: `No se encontró ningún archivo vm_data_*.json`

Asegúrate de ejecutar `collect.py` antes que `analyze.py`, y que ambos scripts están en la misma carpeta.

### Las alertas de seguridad aparecen vacías

Azure Security Center necesita el plan **Defender for Cloud** activo. Ve al portal → Microsoft Defender for Cloud → Environment settings y verifica que está habilitado para tu suscripción.

---

## 📁 Estructura final del proyecto

```
azure-security-claude/
├── collect.py                  ← recoge datos de Azure
├── analyze.py                  ← analiza con Claude
├── vm_data_<nombre>.json       ← datos crudos (generado automáticamente)
└── security_report_<nombre>.md ← informe final (generado automáticamente)
```

---

*Proyecto creado con Claude AI — Anthropic*
