from src.configGlobale import ConfigGlobale


def test_config_absente_utilise_les_valeurs_par_defaut(tmp_path):
    config = ConfigGlobale(tmp_path / "absente.ini")

    assert config.get("Application", "last_project_path") == ""
    assert config.getInt("Application", "entier", 7) == 7
    assert config.getFloat("Application", "flottant", 1.5) == 1.5
    assert config.getBool("Application", "booleen", True) is True


def test_config_lit_les_getters_types_depuis_un_ini(tmp_path):
    chemin = tmp_path / "config.ini"
    chemin.write_text(
        "[Application]\ntexte = bonjour\nentier = 12\nflottant = 3.25\nbooleen = yes\n",
        encoding="utf-8",
    )

    config = ConfigGlobale(chemin)

    assert config.get("Application", "texte") == "bonjour"
    assert config.getInt("Application", "entier") == 12
    assert config.getFloat("Application", "flottant") == 3.25
    assert config.getBool("Application", "booleen") is True


def test_config_retourne_les_fallbacks_pour_section_ou_cle_absente(tmp_path):
    config = ConfigGlobale(tmp_path / "config.ini")

    assert config.get("Absente", "cle", "fallback") == "fallback"
    assert config.getInt("Absente", "cle", 9) == 9
    assert config.getFloat("Absente", "cle", 2.5) == 2.5
    assert config.getBool("Absente", "cle", False) is False


def test_set_cree_une_section_et_save_persiste_la_valeur(tmp_path):
    chemin = tmp_path / "config.ini"
    config = ConfigGlobale(chemin)

    config.set("Application", "nom", "Chouette")
    config.save()

    assert chemin.exists()
    assert ConfigGlobale(chemin).get("Application", "nom") == "Chouette"


def test_set_met_a_jour_une_valeur_existante_sur_disque(tmp_path):
    chemin = tmp_path / "config.ini"
    chemin.write_text("[Application]\nmode = ancien\n", encoding="utf-8")
    config = ConfigGlobale(chemin)

    config.set("Application", "mode", "nouveau")
    config.save()

    assert ConfigGlobale(chemin).get("Application", "mode") == "nouveau"


def test_set_convertit_les_valeurs_en_texte_et_les_getters_les_relisent(tmp_path):
    chemin = tmp_path / "config.ini"
    config = ConfigGlobale(chemin)
    config.set("Types", "entier", 12)
    config.set("Types", "flottant", 3.25)
    config.set("Types", "booleen", True)
    config.save()

    relu = ConfigGlobale(chemin)
    assert relu.getInt("Types", "entier") == 12
    assert relu.getFloat("Types", "flottant") == 3.25
    assert relu.getBool("Types", "booleen") is True


def test_last_project_path_est_persiste_avec_espaces_et_antislashs(tmp_path):
    chemin = tmp_path / "config.ini"
    projet = r"D:\Mes projets\Base Cadran.json"
    config = ConfigGlobale(chemin)

    config.set("Application", "last_project_path", projet)
    config.save()

    assert ConfigGlobale(chemin).get("Application", "last_project_path") == projet


def test_valeur_vide_est_persistee_comme_chaine_vide(tmp_path):
    chemin = tmp_path / "config.ini"
    config = ConfigGlobale(chemin)

    config.set("Application", "last_project_path", "")
    config.save()

    assert ConfigGlobale(chemin).get("Application", "last_project_path", "fallback") == ""
