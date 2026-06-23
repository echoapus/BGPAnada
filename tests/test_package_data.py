from importlib import resources


def test_web_ui_packaged_resource_is_available():
    ui = resources.files("bgpx").joinpath("web", "ui.html")

    assert ui.is_file()
    assert "<!DOCTYPE html>" in ui.read_text(encoding="utf-8")
