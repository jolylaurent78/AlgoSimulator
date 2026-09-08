import pytest

from src.ListeSegmentsDataSet import ListeSegmentsDataSet


@pytest.fixture
def dataset_csv_path(tmp_path):
    chemin = tmp_path / "segments.csv"
    chemin.write_text(
        "Evènement,LettreSegment,Extremite1,MilieuSegment,Extremite2,DateSegment,Date,Stylet,LettreDecl,Base1,Base2\n"
        "C,LC,C1,CM,C2,01/01/1000,02/01/1000,SC,DC,BC1,BC2\n"
        "A,LA,A1,AM,A2,03/01/1000,04/01/1000,SA,DA,BA1,BA2\n"
        "B,LB,B1,BM,B2,05/01/1000,06/01/1000,SB,DB,BB1,BB2\n",
        encoding="utf-8",
    )
    return chemin


def test_construction_lit_le_csv_et_conserve_lordre(dataset_csv_path):
    dataset = ListeSegmentsDataSet(dataset_csv_path)

    assert dataset.getValeursSegment() == ["C", "A", "B"]
    assert list(dataset.evenements) == ["C", "A", "B"]
    assert dataset.segment == "C"
    assert dataset.date is None
    assert dataset.extremite1 is None


def test_calculer_projette_tous_les_attributs_du_premier_segment(dataset_csv_path):
    dataset = ListeSegmentsDataSet(dataset_csv_path)

    dataset.calculer()

    assert dataset.lettreSegment == "LC"
    assert dataset.extremite1 == "C1"
    assert dataset.milieuSegment == "CM"
    assert dataset.extremite2 == "C2"
    assert dataset.dateSegment == "01/01/1000"
    assert dataset.date == "02/01/1000"
    assert dataset.stylet == "SC"
    assert dataset.lettreDecl == "DC"
    assert dataset.base1 == "BC1"
    assert dataset.base2 == "BC2"


def test_calculer_suit_le_changement_de_segment_sans_corrompre_les_sources(dataset_csv_path):
    dataset = ListeSegmentsDataSet(dataset_csv_path)
    dataset.segment = "B"
    dataset.calculer()

    assert (dataset.lettreSegment, dataset.extremite1, dataset.date, dataset.base2) == ("LB", "B1", "06/01/1000", "BB2")
    assert dataset.evenements["C"]["Date"] == "02/01/1000"
    dataset.segment = "C"
    dataset.calculer()
    assert dataset.date == "02/01/1000"


def test_get_valeur_pour_segment_est_insensible_a_la_casse(dataset_csv_path):
    dataset = ListeSegmentsDataSet(dataset_csv_path)

    assert dataset.getValeurPourSegment("A", "date") == "04/01/1000"
    assert dataset.getValeurPourSegment("B", "BASE1") == "BB1"


def test_get_valeur_pour_segment_refuse_segment_et_attribut_absents(dataset_csv_path):
    dataset = ListeSegmentsDataSet(dataset_csv_path)

    with pytest.raises(ValueError, match="segment 'INCONNU'.*introuvable"):
        dataset.getValeurPourSegment("INCONNU", "Date")
    with pytest.raises(ValueError, match="attribut 'Inconnu'.*introuvable"):
        dataset.getValeurPourSegment("A", "Inconnu")


def test_calculer_refuse_un_segment_inconnu(dataset_csv_path):
    dataset = ListeSegmentsDataSet(dataset_csv_path)
    dataset.segment = "INCONNU"

    with pytest.raises(ValueError, match="n'existe pas"):
        dataset.calculer()


def test_construction_refuse_un_fichier_absent(tmp_path):
    with pytest.raises(FileNotFoundError):
        ListeSegmentsDataSet(tmp_path / "absent.csv")


def test_valeurs_du_csv_restent_des_chainess(dataset_csv_path):
    dataset = ListeSegmentsDataSet(dataset_csv_path)

    assert dataset.evenements["A"]["Date"] == "04/01/1000"
    assert isinstance(dataset.evenements["A"]["Date"], str)
