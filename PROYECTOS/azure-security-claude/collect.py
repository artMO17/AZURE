import os, json, subprocess
from datetime import datetime
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.security import SecurityCenter
from azure.mgmt.network import NetworkManagementClient

# ── Credenciales (cámbialas aquí directamente) ─────────────
SUBSCRIPTION_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
RESOURCE_GROUP  = "mi-resource-group"
VM_NAME         = "mi-vm"
TENANT_ID       = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
CLIENT_ID       = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
CLIENT_SECRET   = "tu-client-secret"
# ───────────────────────────────────────────────────────────

credential = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
compute  = ComputeManagementClient(credential, SUBSCRIPTION_ID)
security = SecurityCenter(credential, SUBSCRIPTION_ID)
network  = NetworkManagementClient(credential, SUBSCRIPTION_ID)

print("🔍 Recopilando datos de la VM...")

data = {}

# ── Info básica de la VM ───────────────────────────────────
vm = compute.virtual_machines.get(RESOURCE_GROUP, VM_NAME, expand="instanceView")
data["vm_name"]   = vm.name
data["location"]  = vm.location
data["vm_size"]   = vm.hardware_profile.vm_size
data["os_type"]   = str(vm.storage_profile.os_disk.os_type)
data["os_disk"]   = vm.storage_profile.os_disk.name
data["statuses"]  = [s.display_status for s in vm.instance_view.statuses]
data["timestamp"] = datetime.utcnow().isoformat()

# ── Extensiones instaladas ─────────────────────────────────
exts = compute.virtual_machine_extensions.list(RESOURCE_GROUP, VM_NAME)
data["extensions"] = [e.name for e in exts]

# ── Discos y cifrado ───────────────────────────────────────
all_disks = [vm.storage_profile.os_disk] + list(vm.storage_profile.data_disks)
data["disks"] = []
for d in all_disks:
    encryption = "desconocido"
    try:
        disk_obj = compute.disks.get(RESOURCE_GROUP, d.name)
        enc = disk_obj.encryption
        encryption = str(enc.type) if enc else "sin cifrado"
    except:
        pass
    data["disks"].append({
        "name":       d.name,
        "size_gb":    getattr(d, "disk_size_gb", "N/A"),
        "encryption": encryption,
        "type":       "OS" if d == vm.storage_profile.os_disk else "Data"
    })

# ── Reglas de red (NSG) ────────────────────────────────────
data["network"] = []
for nic_ref in vm.network_profile.network_interfaces:
    nic_name = nic_ref.id.split("/")[-1]
    try:
        nic = network.network_interfaces.get(RESOURCE_GROUP, nic_name)
        entry = {"nic": nic_name, "nsg": "Ninguno", "rules": []}

        if nic.network_security_group:
            nsg_name = nic.network_security_group.id.split("/")[-1]
            entry["nsg"] = nsg_name
            nsg = network.network_security_groups.get(RESOURCE_GROUP, nsg_name)
            for r in nsg.security_rules:
                entry["rules"].append({
                    "name":      r.name,
                    "direction": str(r.direction),
                    "access":    str(r.access),
                    "protocol":  str(r.protocol),
                    "src":       r.source_address_prefix,
                    "dst_port":  r.destination_port_range,
                    "priority":  r.priority,
                })
        data["network"].append(entry)
    except Exception as e:
        data["network"].append({"nic": nic_name, "error": str(e)})

# ── IPs públicas ───────────────────────────────────────────
data["public_ips"] = []
for nic_ref in vm.network_profile.network_interfaces:
    nic_name = nic_ref.id.split("/")[-1]
    try:
        nic = network.network_interfaces.get(RESOURCE_GROUP, nic_name)
        for ip_config in nic.ip_configurations:
            if ip_config.public_ip_address:
                pip_name = ip_config.public_ip_address.id.split("/")[-1]
                pip = network.public_ip_addresses.get(RESOURCE_GROUP, pip_name)
                data["public_ips"].append({
                    "name":    pip_name,
                    "address": pip.ip_address,
                    "sku":     str(pip.sku.name) if pip.sku else "N/A",
                })
    except:
        pass

# ── Alertas de Azure Security Center ──────────────────────
data["security_alerts"] = []
try:
    for alert in security.alerts.list_by_resource_group(RESOURCE_GROUP):
        if VM_NAME.lower() in str(alert.compromised_entity or "").lower():
            data["security_alerts"].append({
                "title":       alert.display_name,
                "severity":    str(alert.severity),
                "status":      str(alert.status),
                "description": alert.description,
                "remediation": getattr(alert, "remediation_steps", "N/A"),
                "time":        str(alert.time_generated_utc),
            })
except Exception as e:
    data["security_alerts"].append({"error": str(e)})

# ── Guardar JSON ───────────────────────────────────────────
output_file = f"vm_data_{VM_NAME}.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✅ Datos guardados en: {output_file}")
print(f"   • Extensiones:      {len(data['extensions'])}")
print(f"   • Discos:           {len(data['disks'])}")
print(f"   • IPs públicas:     {len(data['public_ips'])}")
print(f"   • Reglas NSG:       {sum(len(n.get('rules', [])) for n in data['network'])}")
print(f"   • Alertas:          {len(data['security_alerts'])}")