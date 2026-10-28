"""Démarrage et annulation de calibration avec la carte Extended conservée."""
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

import src.carte_config as carto
import src.configGlobale as config_module
import src.interface_tk as interface_module
from src.configGlobale import ConfigGlobale
from src.interface_tk import InterfaceCarte


EXTENDED = "data/carto/899 - extended v2 corse_calibree.json"


@pytest.mark.parametrize("contenu", ["", "[Carte]\n", f"[Carte]\nlastcarte = {EXTENDED}\n"])
def test_chargement_initial_extended_avec_ou_sans_lastcarte(tmp_path, monkeypatch, contenu):
    ini = tmp_path / "simulateur.ini"
    ini.write_text(contenu, encoding="utf-8")
    configuration = ConfigGlobale(ini)
    monkeypatch.setattr(config_module, "ConfigGlobale", lambda: configuration)
    # Réutiliser les pixels de la véritable image déjà décodée à l'import,
    # tout en contrôlant le chemin demandé par l'initialisation réelle.
    lire_image = Mock(return_value=carto.carteConfig.img)
    monkeypatch.setattr(carto.cv2, "imread", lire_image)

    module = runpy.run_path("src/carte_config.py")

    assert module["dernier_json"] == EXTENDED
    assert module["carteConfig"].image_size == (9999, 9999)
    assert module["carteConfig"].description == "Carte Michelin 899 + Corse"
    lire_image.assert_called_once()
    assert Path(lire_image.call_args.args[0]) == Path(EXTENDED).parent / "899 - extended v2 corse.jpg"
    assert ini.read_text(encoding="utf-8") == contenu


@pytest.mark.parametrize("derniere", [None, "data/carto/autre_calibration.json"])
def test_annulation_calibration_restaure_la_derniere_carte_ou_extended(tmp_path, monkeypatch, derniere):
    ini = tmp_path / "simulateur.ini"
    contenu = "[Carte]\n" + (f"lastcarte = {derniere}\n" if derniere else "")
    ini.write_text(contenu, encoding="utf-8")
    carte = SimpleNamespace(load_from_json=Mock())
    monkeypatch.setattr(interface_module, "carteConfig", carte)
    monkeypatch.setattr(interface_module.filedialog, "askopenfilename", Mock(return_value="nouvelle.jpg"))
    monkeypatch.setattr(interface_module.pd, "read_csv", Mock(return_value={"Nom": ["Paris"]}))
    monkeypatch.setattr(interface_module, "villes_dict", {"Paris": object()})
    monkeypatch.setattr(interface_module.cv2, "imread", Mock(return_value=np.zeros((20, 30, 3), dtype=np.uint8)))
    interface = SimpleNamespace(
        cfg=ConfigGlobale(ini), canvas_image=Mock(), bind=Mock(return_value="escape"),
        unbind=Mock(), _refresh_images=Mock(), _on_right_click=Mock(),
        _on_mouse_move_global=Mock(), _on_right_click_calibrationMode=Mock(),
        annulerCalibration=Mock(), desactiverMesureDistance=Mock(),
    )
    ancien_mouvement = interface._on_mouse_move_global

    InterfaceCarte.demarrerCalibrationNouvelleCarte(interface)
    assert interface._jsonCartePrecedente == (derniere or EXTENDED)
    assert interface.modeCalibration is True
    InterfaceCarte.annulerCalibration(interface)

    carte.load_from_json.assert_called_once_with(derniere or EXTENDED)
    assert interface.modeCalibration is False
    assert interface.carteCalibrationActive is False
    assert interface._on_mouse_move_global is ancien_mouvement
    interface.canvas_image.bind.assert_any_call("<Button-3>", interface._on_right_click)
    assert ini.read_text(encoding="utf-8") == contenu


@pytest.mark.parametrize("lon,lat", [(2.3522, 48.8566), (8.7386, 41.9192), (-1.319, 43.021)])
def test_conversions_reelles_extended_lambert_pixels(lon, lat):
    configuration = carto.carteConfig
    x, y = configuration.gps_to_lambert93(lon, lat)
    pixels = configuration.lambert93_to_pixels(x, y)
    assert configuration.pixels_to_lambert93(*pixels) == pytest.approx((x, y), abs=1e-7)
