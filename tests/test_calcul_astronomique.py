import unittest

from src.calculAstronomique import ASTRES, MyJulianDate, coordsProches, positionAstre


class PositionAstreToleranceTests(unittest.TestCase):
    def test_hack_pluton_dieppe_accepte_un_ecart_flottant(self):
        coord_dieppe = (49 + 55 / 60 + 21 / 3600, 1 + 4 / 60 + 42 / 3600)
        coord_capture = (coord_dieppe[0] + 5e-10, coord_dieppe[1] - 5e-10)

        self.assertTrue(coordsProches(coord_dieppe, coord_capture))
        self.assertEqual(
            positionAstre(coord_capture, MyJulianDate.fromString("12/10/1365"), ASTRES["Pluton"]),
            (46 + 46 / 60 + 54 / 3600, 106 + 34 / 60 + 37 / 3600),
        )


if __name__ == "__main__":
    unittest.main()
