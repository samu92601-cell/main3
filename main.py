import json
import os
import time
import traceback
import requests
import instaloader

#axel es una perrita hermosa y muy inteligente, lo quiero mucho <3

# ── Rutas base ────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.realpath(__file__))
RUTA_JSON   = os.path.join(BASE_DIR, "usuarios.json")
COOKIES_PATH = os.path.join(BASE_DIR, "cookies_ig.json")


# ── Persistencia ──────────────────────────────────────────────────────────────

def cargar_usuarios():
    if not os.path.exists(RUTA_JSON):
        return {}
    try:
        with open(RUTA_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def guardar_usuarios(usuarios):
    with open(RUTA_JSON, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())


# ── Instagram ─────────────────────────────────────────────────────────────────

def crear_sesion_ig(usuario_login):
    """Crea una sesión de instaloader autenticada usando cookies_ig.json."""
    L = instaloader.Instaloader()

    try:
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            cookies = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] No se encontró {COOKIES_PATH}")
        print("  → Exporta tus cookies desde Opera GX con Cookie-Editor y guárdalas como cookies_ig.json")
        return None

    cookie_dict = {c["name"]: c["value"] for c in cookies}
    session_id  = cookie_dict.get("sessionid")
    csrf_token  = cookie_dict.get("csrftoken")

    if not session_id:
        print("[ERROR] No se encontró 'sessionid' en las cookies.")
        return None

    L.context._session.cookies.update({
        "sessionid":  session_id,
        "csrftoken":  csrf_token or "",
        "ds_user_id": cookie_dict.get("ds_user_id", ""),
        "ig_did":     cookie_dict.get("ig_did", ""),
        "mid":        cookie_dict.get("mid", ""),
    })
    L.context._session.headers.update({
        "x-csrftoken":  csrf_token or "",
        "x-ig-app-id":  "936619743392459",
    })
    L.context.username = usuario_login
    return L

def obtener_datos_ig(usuario_login, objetivo):
    """Obtiene seguidores y seguidos de un perfil de Instagram."""
    L = crear_sesion_ig(usuario_login)
    if L is None:
        return None, None

    time.sleep(2)

    try:
        profile = instaloader.Profile.from_username(L.context, objetivo)
        print(f"Perfil encontrado: @{profile.username} ({profile.followers} seguidores)")
    except Exception as e:
        traceback.print_exc()
        print(f"[ERROR] No se pudo obtener el perfil: {e}")
        return None, None

    print("Obteniendo seguidores...  (puede tardar)")
    seguidores = [f.username for f in profile.get_followers()]

    print("Obteniendo seguidos...    (puede tardar)")
    seguidos   = [f.username for f in profile.get_followees()]

    return seguidores, seguidos


# ── Análisis ──────────────────────────────────────────────────────────────────

def analizar(seguidores, seguidos):
    seg_set  = set(seguidores)
    sdo_set  = set(seguidos)
    no_me_siguen = sorted(sdo_set - seg_set)
    yo_no_sigo   = sorted(seg_set - sdo_set)
    mutuos       = sorted(seg_set & sdo_set)
    return no_me_siguen, yo_no_sigo, mutuos

def comparar_cambios(viejo_seg, viejo_sdo, nuevo_seg, nuevo_sdo):
    nuevos_seguidores  = set(nuevo_seg) - set(viejo_seg)
    perdidos           = set(viejo_seg) - set(nuevo_seg)
    nuevos_seguidos    = set(nuevo_sdo) - set(viejo_sdo)
    dejaste_seguir     = set(viejo_sdo) - set(nuevo_sdo)
    return nuevos_seguidores, perdidos, nuevos_seguidos, dejaste_seguir


# ── Helpers de UI ─────────────────────────────────────────────────────────────

def imprimir_lista(titulo, datos):
    print(f"\n{titulo} ({len(datos)}):")
    if not datos:
        print("  - ninguno -")
    else:
        for u in sorted(datos):
            print(f"  - {u}")

def seleccionar_usuario(usuarios):
    print("\nUsuarios guardados:")
    lista = list(usuarios.keys())
    for i, nombre in enumerate(lista, 1):
        print(f"  {i}. {nombre}")
        
    while True:
        try:
            seleccion = int(input("Selecciona un usuario por número: ").strip())
            if 1 <= seleccion <= len(lista):
                return lista[seleccion - 1]
            else:
                print("Número fuera de rango.")
        except ValueError:
            print("Ingresa un número válido.")

def mostrar_menu():
    print("\n" + "─" * 40)
    print("  INSTAGRAM TRACKER")
    print("─" * 40)
    print("  1. Ver análisis de un usuario guardado")
    print("  2. Agregar usuario (con cookies de IG)")
    print("  3. Actualizar usuario y detectar cambios")
    print("  4. Eliminar usuario")
    print("  5. Agregar usuario manualmente (fallback)")
    print("  6. Salir")
    print("─" * 40)


# ── Opciones del menú ─────────────────────────────────────────────────────────

def ver_usuario():
    usuarios = cargar_usuarios()
    if not usuarios:
        print("No hay usuarios guardados.")
        return

    seleccionado = seleccionar_usuario(usuarios)
    if seleccionado not in usuarios:
        print("Usuario no encontrado.")
        return

    datos = usuarios[seleccionado]
    no_me_siguen, yo_no_sigo, mutuos = analizar(datos["seguidores"], datos["seguidos"])

    imprimir_lista("No te siguen de vuelta", no_me_siguen)
    imprimir_lista("No sigues de vuelta",    yo_no_sigo)
    imprimir_lista("Mutuos",                 mutuos)


def agregar_usuario_ig():
    objetivo      = input("Username del perfil a guardar: ").strip()
    usuario_login = input("Tu username de Instagram:      ").strip()

    seguidores, seguidos = obtener_datos_ig(usuario_login, objetivo)
    if seguidores is None:
        print("No se guardaron datos.")
        return

    usuarios = cargar_usuarios()
    usuarios[objetivo] = {"seguidores": seguidores, "seguidos": seguidos}
    guardar_usuarios(usuarios)
    print(f"\n✓ '{objetivo}' guardado — {len(seguidores)} seguidores, {len(seguidos)} seguidos.")


def actualizar_usuario():
    usuarios = cargar_usuarios()
    if not usuarios:
        print("No hay usuarios guardados.")
        return

    seleccionado = seleccionar_usuario(usuarios)
    if seleccionado not in usuarios:
        print("Usuario no encontrado.")
        return

    usuario_login = input("Tu username de Instagram: ").strip()

    print(f"\nObteniendo datos actualizados de @{seleccionado}...")
    nuevos_seg, nuevos_sdo = obtener_datos_ig(usuario_login, seleccionado)
    if nuevos_seg is None:
        print("No se pudo actualizar.")
        return

    datos = usuarios[seleccionado]
    ganados, perdidos, ahora_sigues, dejaste = comparar_cambios(
        datos["seguidores"], datos["seguidos"],
        nuevos_seg, nuevos_sdo
    )

    imprimir_lista("Nuevos seguidores",     ganados)
    imprimir_lista("Seguidores perdidos",   perdidos)
    imprimir_lista("Ahora sigues a",        ahora_sigues)
    imprimir_lista("Dejaste de seguir a",   dejaste)

    usuarios[seleccionado] = {"seguidores": nuevos_seg, "seguidos": nuevos_sdo}
    guardar_usuarios(usuarios)
    print(f"\n✓ '{seleccionado}' actualizado correctamente.")


def eliminar_usuario():
    usuarios = cargar_usuarios()
    if not usuarios:
        print("No hay usuarios guardados.")
        return

    seleccionado = seleccionar_usuario(usuarios)
    if seleccionado not in usuarios:
        print("Usuario no encontrado.")
        return

    confirmar = input(f"¿Seguro que quieres eliminar '{seleccionado}'? (s/n): ").strip().lower()
    if confirmar == "s":
        del usuarios[seleccionado]
        guardar_usuarios(usuarios)
        print(f"✓ '{seleccionado}' eliminado.")
    else:
        print("Cancelado.")


def agregar_usuario_manual():
    print("\n⚠ Modo manual: Instagram no muestra todos los usuarios en sus listas.")
    print("  Úsalo solo si las cookies no funcionan.\n")

    objetivo   = input("Username del perfil: ").strip()
    seguidores = []
    seguidos   = []

    print("Pega los seguidores uno por línea (línea vacía para terminar):")
    while True:
        linea = input().strip()
        if not linea:
            break
        seguidores.append(linea.lower())

    print("Pega los seguidos uno por línea (línea vacía para terminar):")
    while True:
        linea = input().strip()
        if not linea:
            break
        seguidos.append(linea.lower())

    usuarios = cargar_usuarios()
    usuarios[objetivo] = {"seguidores": seguidores, "seguidos": seguidos}
    guardar_usuarios(usuarios)
    print(f"✓ '{objetivo}' guardado manualmente.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    while True:
        mostrar_menu()
        try:
            opcion = int(input("Opción: ").strip())
        except ValueError:
            print("Ingresa un número válido.")
            continue

        if   opcion == 1: ver_usuario()
        elif opcion == 2: agregar_usuario_ig()
        elif opcion == 3: actualizar_usuario()
        elif opcion == 4: eliminar_usuario()
        elif opcion == 5: agregar_usuario_manual()
        elif opcion == 6:
            print("Saliendo...")
            break
        else:
            print("Opción inválida.")

if __name__ == "__main__":
    main()
