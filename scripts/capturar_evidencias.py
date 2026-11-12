import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SALIDA = ROOT / "evidencias"
PUERTO = int(os.getenv("PUERTO_PRUEBAS", "8765"))
URL = f"http://127.0.0.1:{PUERTO}"


def esperar_servidor(servidor):
    for _ in range(60):
        if servidor.poll() is not None:
            raise RuntimeError("El servidor se cerró al arrancar")
        try:
            with urllib.request.urlopen(URL + "/api/health", timeout=1) as respuesta:
                if respuesta.status == 200:
                    return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError("El servidor no respondió a tiempo")


def recorrer_app(pagina):
    pagina.goto(URL)
    expect(pagina.locator("#statOffers")).to_have_text("3")
    pagina.screenshot(path=SALIDA / "01_panel_funcional.png", full_page=True)

    pagina.get_by_role("button", name="Publicar oferta").first.click()
    pagina.get_by_label("Título de la vacante").fill("Practicante de Automatización")
    pagina.get_by_label("Descripción de actividades").fill("Automatizar pruebas de la API y de la interfaz web.")
    pagina.get_by_label("Modalidad").select_option("Remota")
    pagina.screenshot(path=SALIDA / "02_publicar_oferta.png", full_page=True)
    pagina.locator("#offerForm button[type=submit]").click()
    expect(pagina.locator("#notification")).to_contain_text("quedó publicada")
    expect(pagina.locator("#offerCount")).to_have_text("4 ofertas abiertas")
    expect(pagina.locator("#offerCards")).to_contain_text("Practicante de Automatización")
    pagina.screenshot(path=SALIDA / "03_catalogo_ofertas.png", full_page=True)

    pagina.locator(".offer-card", has_text="Practicante de Automatización").get_by_role("button", name="Postularme").click()
    expect(pagina.locator("#notification")).to_contain_text("Postulación registrada")
    pagina.get_by_role("button", name="Mis postulaciones").click()
    expect(pagina.locator("#myApplications .app-row")).to_have_count(1)
    expect(pagina.locator("#myApplications")).to_contain_text("Pendiente")
    pagina.screenshot(path=SALIDA / "04_postulacion_pendiente.png", full_page=True)

    pagina.get_by_role("button", name="Coordinación").click()
    expect(pagina.locator("#reviewList .app-row")).to_have_count(1)
    pagina.screenshot(path=SALIDA / "05_bandeja_revision.png", full_page=True)
    pagina.get_by_role("button", name="Aprobar").click()
    expect(pagina.locator("#reviewList")).to_contain_text("Aprobada")

    pagina.get_by_role("button", name="Mis postulaciones").click()
    expect(pagina.locator("#myApplications")).to_contain_text("Aprobada")
    pagina.screenshot(path=SALIDA / "06_postulacion_aprobada.png", full_page=True)


def main():
    SALIDA.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
        entorno = {**os.environ, "PRACTICAS_DB": str(Path(carpeta) / "e2e.db")}
        servidor = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(PUERTO)],
            cwd=ROOT,
            env=entorno,
        )
        try:
            esperar_servidor(servidor)
            with sync_playwright() as p:
                navegador = p.chromium.launch()
                pagina = navegador.new_page(viewport={"width": 1440, "height": 900})
                errores = []
                pagina.on("pageerror", lambda e: errores.append(str(e)))
                recorrer_app(pagina)
                navegador.close()
            if errores:
                raise AssertionError(f"Errores de JavaScript: {errores}")
        finally:
            servidor.terminate()
            try:
                servidor.wait(timeout=5)
            except subprocess.TimeoutExpired:
                servidor.kill()

    resumen = "Recorrido e2e OK: publicar -> postular -> revisar, sin errores de JavaScript"
    (SALIDA / "resultado_e2e.txt").write_text(resumen + "\n", encoding="utf-8")
    print(resumen)


if __name__ == "__main__":
    main()
