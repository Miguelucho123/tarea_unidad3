import pytest
from fastapi.testclient import TestClient

import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "DB_PATH", tmp_path / "tests.db")
    with TestClient(app_module.app) as c:
        yield c


def test_publicar_oferta_valida(client):
    payload = {
        "empresa_id": 1,
        "titulo": "Prácticas en ingeniería de software",
        "descripcion": "Desarrollar APIs y ejecutar pruebas automatizadas.",
        "modalidad": "Remota",
    }
    r = client.post("/api/ofertas", json=payload)
    assert r.status_code == 201
    assert r.json()["estado"] == "Abierta"
    assert any(o["titulo"] == payload["titulo"] for o in client.get("/api/ofertas").json())


def test_postulacion_crea_estado_pendiente(client):
    r = client.post("/api/postulaciones", json={"oferta_id": 1, "estudiante_id": 1})
    assert r.status_code == 201
    assert r.json()["estado"] == "Pendiente"
    assert client.get("/api/postulaciones?estudiante_id=1").json()[0]["estado"] == "Pendiente"


def test_postulacion_duplicada_rechazada(client):
    payload = {"oferta_id": 1, "estudiante_id": 1}
    assert client.post("/api/postulaciones", json=payload).status_code == 201
    r = client.post("/api/postulaciones", json=payload)
    assert r.status_code == 409
    assert "ya se postuló" in r.json()["detail"]


def test_aprobacion_y_segunda_revision_bloqueada(client):
    post = client.post("/api/postulaciones", json={"oferta_id": 1, "estudiante_id": 1}).json()
    r = client.patch(f"/api/postulaciones/{post['id']}", json={"decision": "Aprobada"})
    assert r.status_code == 200
    assert r.json()["estado"] == "Aprobada"
    again = client.patch(f"/api/postulaciones/{post['id']}", json={"decision": "Rechazada"})
    assert again.status_code == 409


def test_publicacion_empresa_inexistente(client):
    r = client.post("/api/ofertas", json={
        "empresa_id": 999,
        "titulo": "Título válido",
        "descripcion": "Descripción suficientemente detallada.",
        "modalidad": "Remota",
    })
    assert r.status_code == 404


def test_integracion_flujo_completo(client):
    oferta = client.post("/api/ofertas", json={
        "empresa_id": 2,
        "titulo": "Practicante de soporte técnico",
        "descripcion": "Gestión de incidentes y manuales de operación.",
        "modalidad": "Híbrida",
    }).json()
    post = client.post("/api/postulaciones", json={"oferta_id": oferta["id"], "estudiante_id": 2}).json()
    cambio = client.patch(f"/api/postulaciones/{post['id']}", json={"decision": "Aprobada"}).json()
    assert cambio["estado"] == "Aprobada"
    docs = client.get("/api/postulaciones?estudiante_id=2").json()
    assert len(docs) == 1
    assert docs[0]["oferta_id"] == oferta["id"]
    assert docs[0]["estado"] == "Aprobada"
