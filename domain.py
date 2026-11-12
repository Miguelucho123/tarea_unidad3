def publicacion_valida(titulo: str, descripcion: str) -> bool:
    return len(titulo.strip()) >= 5 and len(descripcion.strip()) >= 12


def oferta_acepta_postulaciones(estado: str) -> bool:
    return estado == "Abierta"


def revision_permitida(estado_actual: str, decision: str) -> bool:
    return estado_actual == "Pendiente" and decision in {"Aprobada", "Rechazada"}
