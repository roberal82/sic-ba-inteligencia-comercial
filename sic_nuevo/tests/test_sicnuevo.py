import sys, unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sicnuevo import alertas, parsers, scoring, store
from sicnuevo.models import Cobro
from sicnuevo.money import parse_monto
from sicnuevo.reglas import cargar_reglas

COBROS = """REPORTE CUENTAS A COBRAR
CLIENTE: ACME SA
MONEDA: PYG
01/01/2026 001-0001 01/02/2026 1.000.000 400.000
CLIENTE: BETA SRL
MONEDA: USD
01/02/2026 001-0002 05/03/2026 2.000,50 2.000,50
"""
PAGOS = """CUENTAS A PAGAR
PROVEEDOR: PROV UNO
MONEDA: PYG
01/03/2026 F-9 12/03/2026 500.000 500.000
"""
CHEQUES = """CHEQUES DIFERIDOS
MONEDA: PYG
000123 | BANCO X | PROV UNO | 14/03/2026 | 5.000.000
"""
HOY = date(2026, 3, 10)


def db():
    con = store.abrir()
    for tipo, txt in (("cobros", COBROS), ("pagos", PAGOS), ("cheques", CHEQUES)):
        store.cargar(con, parsers.ADAPTADORES[tipo].parsear(txt))
    return con


class Tests(unittest.TestCase):
    def test_monto_es_py(self):
        self.assertEqual(parse_monto("2.000,50"), 2000.50)

    def test_deteccion(self):
        self.assertEqual(parsers.detectar(COBROS), "cobros")
        self.assertEqual(parsers.detectar(CHEQUES), "cheques")
        self.assertIsNone(parsers.detectar("otro"))

    def test_parser_cobros_moneda_por_cliente(self):
        f = parsers.cobros.parsear(COBROS)
        self.assertEqual([(x.cliente, x.moneda, x.saldo) for x in f],
                         [("ACME SA", "PYG", 400000.0), ("BETA SRL", "USD", 2000.5)])

    def test_cheques_tienen_parser(self):
        self.assertEqual(len(parsers.cheques.parsear(CHEQUES)), 1)

    def test_carga_idempotente(self):
        con = db()
        store.cargar(con, parsers.cobros.parsear(COBROS))
        self.assertEqual(con.execute("SELECT COUNT(*) FROM cobros").fetchone()[0], 2)

    def test_validacion_rechaza_moneda(self):
        with self.assertRaises(ValueError):
            Cobro("X", "1", HOY, HOY, "EUR", 1, 1)

    def test_alertas_no_mezclan_monedas(self):
        r = cargar_reglas()
        al = alertas.alertas_cobranza(db(), HOY, r)
        self.assertEqual({(a["moneda"]) for a in al}, {"PYG", "USD"})
        acme = next(a for a in al if "ACME" in a["titulo"])
        self.assertEqual(acme["nivel"], "ROJO")  # 37 dias de atraso >= 30
        self.assertEqual(acme["version_reglas"], r.version)

    def test_ventana_vencimientos(self):
        al = alertas.alertas_vencimientos(db(), HOY, cargar_reglas())
        self.assertEqual({a["modulo"] for a in al}, {"Proveedores", "Tesoreria"})

    def test_score_siempre_en_rango_y_discrimina(self):
        r = cargar_reglas()
        s = scoring.score_clientes({"A": 100, "B": 10}, {"A": 5, "B": 1}, {"A": 0, "B": 90}, r)
        self.assertTrue(all(0 <= f["score"] <= 100 for f in s))
        self.assertEqual(s[0]["cliente"], "A")
        self.assertNotEqual(s[0]["score"], s[1]["score"])  # el bug del original igualaba a todos

    def test_liquidez(self):
        r = cargar_reglas()
        self.assertEqual(alertas.semaforo_liquidez(100, 100, 0, r)["nivel"], "AMARILLO")
        self.assertEqual(alertas.semaforo_liquidez(50, 100, 0, r)["nivel"], "ROJO")
        self.assertEqual(alertas.semaforo_liquidez(130, 100, 0, r)["nivel"], "VERDE")


if __name__ == "__main__":
    unittest.main()
