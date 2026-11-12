from domain import oferta_acepta_postulaciones, publicacion_valida, revision_permitida


def test_unit_publicacion_rechaza_titulo_vacio():
    assert not publicacion_valida("        ", "Descripción suficientemente clara")
    assert publicacion_valida("Vacante QA", "Construcción de pruebas de software")


def test_unit_oferta_cerrada_no_admite_postulaciones():
    assert oferta_acepta_postulaciones("Abierta")
    assert not oferta_acepta_postulaciones("Cerrada")


def test_unit_transicion_estado_controlada():
    assert revision_permitida("Pendiente", "Aprobada")
    assert not revision_permitida("Aprobada", "Rechazada")
    assert not revision_permitida("Pendiente", "En proceso")
