from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from domain import publicacion_valida, oferta_acepta_postulaciones, revision_permitida

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("PRACTICAS_DB", str(BASE_DIR / "data" / "demo.db")))


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def setup_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS empresa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            razon_social TEXT NOT NULL, nit TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS estudiante (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            programa TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS oferta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL REFERENCES empresa(id),
            titulo TEXT NOT NULL, descripcion TEXT NOT NULL,
            modalidad TEXT NOT NULL CHECK (modalidad IN ('Remota','Híbrida','Presencial')),
            estado TEXT NOT NULL DEFAULT 'Abierta' CHECK (estado IN ('Abierta','Cerrada')),
            fecha_creacion TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS postulacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oferta_id INTEGER NOT NULL REFERENCES oferta(id),
            estudiante_id INTEGER NOT NULL REFERENCES estudiante(id),
            estado TEXT NOT NULL DEFAULT 'Pendiente'
              CHECK (estado IN ('Pendiente','Aprobada','Rechazada')),
            fecha_creacion TEXT NOT NULL DEFAULT (datetime('now')),
            fecha_revision TEXT,
            UNIQUE (oferta_id, estudiante_id)
        );
        """)
        if db.execute("SELECT COUNT(*) FROM empresa").fetchone()[0] == 0:
            db.executemany("INSERT INTO empresa(razon_social,nit) VALUES (?,?)", [
                ("Tecnología Horizonte S.A.S.","900111222-3"),
                ("Innovación Andina S.A.S.","900444555-6")
            ])
        if db.execute("SELECT COUNT(*) FROM estudiante").fetchone()[0] == 0:
            db.executemany("INSERT INTO estudiante(nombre,email,programa) VALUES (?,?,?)", [
                ("Laura Pérez", "laura.perez@ejemplo.edu.co", "Ingeniería Informática"),
                ("Andrés Gómez", "andres.gomez@ejemplo.edu.co", "Administración de Empresas")
            ])
        if db.execute("SELECT COUNT(*) FROM oferta").fetchone()[0] == 0:
            db.executemany("INSERT INTO oferta(empresa_id,titulo,descripcion,modalidad) VALUES (?,?,?,?)", [
                (1,"Practicante de Desarrollo Web","Colaborar en interfaces web, APIs y documentación de entregables.","Remota"),
                (2,"Practicante de Análisis de Datos","Apoyar tableros, controles de calidad de datos y análisis.","Híbrida"),
                (1,"Practicante de QA","Diseñar casos de prueba, ejecutar regresiones y registrar hallazgos.","Presencial")
            ])
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_db()
    yield


app = FastAPI(title="Prácticas UCN - Taller 3", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class OfertaCrear(BaseModel):
    empresa_id: int = Field(gt=0)
    titulo: str = Field(min_length=5, max_length=100)
    descripcion: str = Field(min_length=12, max_length=1000)
    modalidad: Literal["Remota", "Híbrida", "Presencial"]


class PostulacionCrear(BaseModel):
    oferta_id: int = Field(gt=0)
    estudiante_id: int = Field(gt=0)


class RevisarPostulacion(BaseModel):
    decision: Literal["Aprobada", "Rechazada"]


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health():
    return {
        "estado": "ok",
        "version": "0.1.0",
        "ambiente": os.getenv("AMBIENTE", "local"),
        "commit": os.getenv("RENDER_GIT_COMMIT", "local"),
    }


@app.get("/api/empresas")
def empresas():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT id,razon_social FROM empresa ORDER BY id")]


@app.get("/api/estudiantes")
def estudiantes():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT id,nombre,programa FROM estudiante ORDER BY id")]


@app.get("/api/ofertas")
def ofertas():
    with connect() as db:
        return [dict(r) for r in db.execute("""
        SELECT o.*,e.razon_social AS empresa FROM oferta o
        JOIN empresa e ON e.id=o.empresa_id
        ORDER BY o.id DESC""")]


@app.post("/api/ofertas", status_code=201)
def crear_oferta(nueva: OfertaCrear):
    if not publicacion_valida(nueva.titulo, nueva.descripcion):
        raise HTTPException(422, "Título o descripción sin contenido suficiente")
    with connect() as db:
        if not db.execute("SELECT 1 FROM empresa WHERE id=?", (nueva.empresa_id,)).fetchone():
            raise HTTPException(404, "Empresa no encontrada")
        cur = db.execute("""INSERT INTO oferta(empresa_id,titulo,descripcion,modalidad)
            VALUES (?,?,?,?)""", (nueva.empresa_id, nueva.titulo.strip(),
            nueva.descripcion.strip(), nueva.modalidad))
        db.commit()
        return {"id": cur.lastrowid, "estado": "Abierta", "mensaje": "Oferta publicada"}


@app.get("/api/postulaciones")
def postulaciones(estudiante_id: int | None = None):
    with connect() as db:
        sql = """SELECT p.*, o.titulo AS oferta, e.razon_social AS empresa,
          s.nombre AS estudiante FROM postulacion p
          JOIN oferta o ON p.oferta_id=o.id
          JOIN empresa e ON o.empresa_id=e.id
          JOIN estudiante s ON p.estudiante_id=s.id"""
        params = ()
        if estudiante_id is not None:
            sql += " WHERE p.estudiante_id=?"
            params = (estudiante_id,)
        sql += " ORDER BY p.id DESC"
        return [dict(r) for r in db.execute(sql, params)]


@app.post("/api/postulaciones", status_code=201)
def crear_postulacion(nueva: PostulacionCrear):
    with connect() as db:
        oferta = db.execute("SELECT estado FROM oferta WHERE id=?", (nueva.oferta_id,)).fetchone()
        if oferta is None:
            raise HTTPException(404, "Oferta no encontrada")
        if not oferta_acepta_postulaciones(oferta["estado"]):
            raise HTTPException(409, "La oferta no está abierta")
        if not db.execute("SELECT 1 FROM estudiante WHERE id=?", (nueva.estudiante_id,)).fetchone():
            raise HTTPException(404, "Estudiante no encontrado")
        try:
            cur = db.execute("INSERT INTO postulacion(oferta_id,estudiante_id) VALUES(?,?)",
                             (nueva.oferta_id, nueva.estudiante_id))
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(409, "El estudiante ya se postuló a esta oferta")
        return {"id": cur.lastrowid, "estado": "Pendiente", "mensaje": "Postulación registrada"}


@app.patch("/api/postulaciones/{id_postulacion}")
def revisar_postulacion(id_postulacion: int, revision: RevisarPostulacion):
    with connect() as db:
        estado = db.execute("SELECT estado FROM postulacion WHERE id=?",
                            (id_postulacion,)).fetchone()
        if estado is None:
            raise HTTPException(404, "Postulación no encontrada")
        if not revision_permitida(estado["estado"], revision.decision):
            raise HTTPException(409, "La postulación ya fue revisada")
        db.execute("UPDATE postulacion SET estado=?,fecha_revision=datetime('now') WHERE id=?",
                   (revision.decision, id_postulacion))
        db.commit()
        return {"id": id_postulacion, "estado": revision.decision, "mensaje": "Revisión registrada"}
