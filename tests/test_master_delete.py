from app.documents.master import delete_master


def test_deletes_master_and_backup(tmp_path):
    master = tmp_path / "master_cv.yaml"
    backup = tmp_path / "master_cv.yaml.bak"
    master.write_text("header: {}")
    backup.write_text("header: {}")
    assert delete_master(master)
    assert not master.exists()
    assert not backup.exists()


def test_missing_master_returns_false(tmp_path):
    assert not delete_master(tmp_path / "master_cv.yaml")
