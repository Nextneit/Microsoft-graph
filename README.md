# graph-audit

Reto técnico: auditoría de un tenant de Microsoft 365 mediante Microsoft Graph, con una aplicación registrada en Entra ID con **permisos de solo lectura** y un informe de hallazgos con severidad (usuarios invitados, roles, MFA, licencias).

## Estado

| Fase | Descripción | Estado |
|---|---|---|
| 0 | Registro de la app, permisos y consentimiento | Completada |
| 1 | Autenticación y lectura de 5 usuarios con un token | Completada |
| 2 | Módulos de hallazgos (invitados, roles, MFA, licencias) | Pendiente |
| 3 | Modelo de severidad e informe (JSON/HTML) | Pendiente |

## Estructura

```
graph-audit/
├── .env              # TENANT_ID y CLIENT_ID (no se sube a git)
├── .gitignore        # .env y .token_cache.json
├── requirements.txt
├── auth.py           # autenticación delegada (device code) con caché de token
├── graph_client.py   # cliente HTTP con paginación (@odata.nextLink)
└── main.py           # fase 1: lista 5 usuarios
```

## Requisitos

- Python 3.10+
- Dependencias: `msal`, `requests`, `python-dotenv`

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configuración

Crea un `.env` en la raíz:

```
TENANT_ID=<id-del-directorio-inquilino>
CLIENT_ID=<id-de-aplicacion-cliente>
```

No hace falta `CLIENT_SECRET`: el flujo usado es de cliente público (device code).

## Ejecución

```bash
python3 main.py
```

La primera vez muestra una URL (`https://login.microsoft.com/device`) y un código. Se abre en el navegador, se inicia sesión con el usuario del reto y se acepta. Las siguientes ejecuciones reutilizan la caché (`.token_cache.json`) sin pedir nada.

Salida esperada: los scopes del token (`scp`) y 5 usuarios con nombre, UPN, tipo y estado de la cuenta.

## Proceso seguido

### 1. Registro de la aplicación

En el Centro de administración de Microsoft Entra: **Identidad > Aplicaciones > Registros de aplicaciones > Nuevo registro**, nombre `reto-graph`, solo un inquilino (*Solo mi organización*).

### 2. Permisos de API (Microsoft Graph, solo lectura)

| Permiso | Para qué se usa |
|---|---|
| `User.Read.All` | Usuarios e invitados |
| `Directory.Read.All` | Roles, licencias, estructura del directorio |
| `AuditLog.Read.All` | `signInActivity` (cuentas inactivas) |
| `Policy.Read.All` | Políticas de acceso condicional |
| `RoleManagement.Read.Directory` | Asignaciones de roles |
| `UserAuthenticationMethod.Read.All` | Métodos de autenticación (MFA) |

Todos son de lectura: no hay ningún permiso de escritura.

### 3. Consentimiento de administrador

El usuario del reto tiene el rol *Administrador de aplicaciones en la nube*, que **no puede consentir permisos de Microsoft Graph**, por lo que el botón *Conceder consentimiento de administrador* aparecía deshabilitado. Se resolvió obteniendo el consentimiento (mediante un rol con privilegios o un administrador del tenant). El consentimiento se verifica en **Permisos de API**: la columna *Estado* debe mostrar "Concedido para <organización>".

### 4. Permisos de aplicación frente a delegados

Primer intento: flujo *client credentials* con permisos de **aplicación**. El consentimiento concedido terminó siendo de tipo **Delegada**, y el token de client credentials llevaba cero permisos (claim `roles` vacío), lo que provocaba un `403 Forbidden` en `/users`.

Como el reto pide permisos delegados, se cambió el código al flujo correspondiente:

- Se pasó de `ConfidentialClientApplication` a `PublicClientApplication`.
- Autenticación por **device code**, con caché de token serializada en disco.
- Los permisos efectivos se leen del claim `scp` del token, no de `roles`.

### 5. Error `AADSTS7000218` y su solución

Tras iniciar sesión con device code apareció: *The request body must contain the following parameter: 'client_assertion' or 'client_secret'*. La app seguía tratada como cliente confidencial. Se solucionó en **Authentication > Permitir flujos de cliente público = Sí** (alternativa: añadir la plataforma *Aplicaciones móviles y de escritorio*).

## Notas de diseño

- **Seguridad:** `.env` y `.token_cache.json` están en `.gitignore`; no se versionan secretos ni tokens. Mínimo privilegio: solo permisos de lectura.
- **Paginación:** `GraphClient.get_all()` sigue `@odata.nextLink`, necesaria para invitados, licencias y MFA en tenants con muchos usuarios.
- **Limitación del modo delegado:** los permisos efectivos son la intersección entre los scopes de la app y los roles del usuario. Con el rol actual, algunos endpoints pueden devolver 403 aunque el scope esté concedido:
  - `signInActivity` e informes de métodos de autenticación suelen requerir *Lector de informes* o *Lector de seguridad*.
  - `/users/{id}/authentication/methods` suele requerir *Administrador de autenticación*.

  Los hallazgos que no se puedan evaluar por este motivo se reflejarán en el informe como "no evaluable por permisos insuficientes", con severidad informativa, en lugar de omitirse.

## Siguientes pasos

1. Módulos por hallazgo en `findings/` (`guests.py`, `roles.py`, `mfa.py`, `licenses.py`), cada uno devolviendo objetos con `severity`, `title` y `evidence`.
2. Modelo de severidad documentado, por ejemplo:
   - **Crítica:** administrador global sin MFA.
   - **Alta:** invitado con rol privilegiado.
   - **Media:** cuentas inactivas con licencia asignada.
   - **Baja / Info:** resto de observaciones y datos no evaluables.
3. Generación del informe (JSON y HTML) con resumen por severidad.

| Hallazgo | Endpoint |
|---|---|
| Usuarios invitados | `/users?$filter=userType eq 'Guest'` |
| Roles privilegiados | `/directoryRoles` y `/directoryRoles/{id}/members` |
| MFA | `/users/{id}/authentication/methods` o `/reports/authenticationMethods/userRegistrationDetails` |
| Licencias | `/subscribedSkus` y `assignedLicenses` en `/users` |
| Cuentas inactivas | `signInActivity` en `/users` |