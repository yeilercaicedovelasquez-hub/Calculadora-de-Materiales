import unittest

from server import calcular


class CalculadoraTests(unittest.TestCase):
    def test_muro_20_cm_matches_pdf_example(self):
        result, _ = calcular("muro", {"espesor": 20, "largo": 10, "alto": 15})
        self.assertEqual(result["superficie"], 150.0)
        self.assertEqual(result["cemento"], 1635.0)
        self.assertEqual(result["arena"], 13.5)
        self.assertEqual(result["ladrillos"], 13500)

    def test_muro_30_cm_coefficients(self):
        result, _ = calcular("muro", {"espesor": 30, "largo": 10, "alto": 15})
        self.assertEqual(result["cemento"], 2280.0)
        self.assertEqual(result["arena"], 17.25)
        self.assertEqual(result["ladrillos"], 18000)

    def test_viga(self):
        result, _ = calcular("viga", {"largo": 1})
        self.assertEqual(result["cemento"], 9.0)
        self.assertEqual(result["arena"], 0.02)
        self.assertEqual(result["hierro8"], 4.0)

    def test_columna(self):
        result, _ = calcular("columna", {"largo": 1})
        self.assertEqual(result["cemento"], 7.5)
        self.assertEqual(result["arena"], 0.016)
        self.assertEqual(result["hierro10"], 6.0)

    def test_contrapiso_matches_pdf_example(self):
        result, _ = calcular("contrapiso", {"espesor": 5, "ancho": 15, "largo": 20})
        self.assertEqual(result["volumen"], 1500.0)
        self.assertEqual(result["cemento"], 157500.0)
        self.assertEqual(result["arena"], 675.0)
        self.assertEqual(result["piedra"], 1350.0)

    def test_techo(self):
        result, _ = calcular("techo", {"espesor": 1, "ancho": 1, "largo": 1})
        self.assertEqual(result["superficie"], 1.0)
        self.assertEqual(result["cemento"], 33.0)
        self.assertEqual(result["hierro8"], 7.0)

    def test_pisos_ten_percent_cut(self):
        result, _ = calcular("pisos", {"ancho": 1, "largo": 1})
        self.assertEqual(result["superficieNeta"], 1.0)
        self.assertEqual(result["superficieConRecorte"], 1.1)

    def test_pintura_six_square_meters_per_liter(self):
        result, _ = calcular("pintura", {"superficie": 6})
        self.assertEqual(result["litros"], 1.0)

    def test_rejects_zero_and_unknown_calculation(self):
        with self.assertRaises(ValueError):
            calcular("viga", {"largo": 0})
        with self.assertRaises(ValueError):
            calcular("otro", {})
        with self.assertRaises(ValueError):
            calcular("muro", {"espesor": 20.5, "largo": 2, "alto": 2})
        with self.assertRaises(ValueError):
            calcular("pintura", {"superficie": 1_000_001})


if __name__ == "__main__":
    unittest.main(verbosity=2)
