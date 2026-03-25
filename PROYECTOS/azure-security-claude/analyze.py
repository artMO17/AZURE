import os, json, sys
from anthropic import Anthropic

# ── Config ─────────────────────────────────────────────────
ANTHROPIC_API_KEY = "sk-ant-..."          # tu API key
JSON_FILE         = sys.argv[1] if len(sys.argv) > 1 else None
# ───────────────────────────────────────────────────────────

if not JSON_FILE:
    # Busca automáticamente el JSON más reciente
    import glob
    files = sorted(glob.glob("vm_data_*.json"), key=os.path.getmtime, reverse=True)
    if not files:
        print("❌ No se encontró ningún archivo vm_data_*.json")
        print("   Ejecuta primero: python collect.py")
        sys.exit(1)
    JSON_FILE = files[0]
    print(f"📂 Usando: {JSON_FILE}\n")

with open(JSON_FILE, "r", encoding="utf-8") as f:
    vm_data = json.load(f)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

print(f"🤖 Analizando seguridad de '{vm_data['vm_name']}' con Claude...\n")
print("─" * 60)

response = client.messages.create(
    model      = "claude-opus-4-20250514",
    max_tokens = 4096,
    system     = """Eres un analista experto en ciberseguridad especializado en 
Azure. Analiza los datos de la VM y genera un informe en español con estas secciones:

🔎 RESUMEN EJECUTIVO
   Estado general: CRÍTICO / ALTO / MEDIO / BAJO

🔴 VULNERABILIDADES CRÍTICAS Y ALTAS
   Lista con descripción y por qué es peligroso

🟡 RIESGOS MEDIOS Y BAJOS
   Lista con descripción

🌐 ANÁLISIS DE RED
   Reglas NSG problemáticas, puertos expuestos, IPs públicas

🚨 ALERTAS ACTIVAS DE AZURE
   Interpretación de cada alerta con contexto

🛡️ QUÉ FALTA INSTALAR
   Extensiones/agentes de seguridad ausentes

✅ PLAN DE ACCIÓN (ordenado por urgencia)
   Pasos concretos con comandos Azure CLI cuando sea posible

Sé directo, específico con los nombres reales de recursos, y sin relleno.""",
    messages   = [{
        "role":    "user",
        "content": f"Analiza esta VM:\n\n```json\n{json.dumps(vm_data, indent=2, ensure_ascii=False)}\n```"
    }]
)

report = response.content[0].text
print(report)

# ── Guardar informe ────────────────────────────────────────
vm_name      = vm_data["vm_name"]
output_file  = f"security_report_{vm_name}.md"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(f"# Informe de Seguridad — {vm_name}\n")
    f.write(f"*Generado: {vm_data['timestamp']}*\n\n")
    f.write(report)

print(f"\n{'─' * 60}")
print(f"✅ Informe guardado en: {output_file}")