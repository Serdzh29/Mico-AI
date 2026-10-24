"""Новая схема версий M26.10.24: текущий номер, сравнение со старыми, теги GitHub, журнал изменений."""
import os as _os
import sys

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import updatecheck as U  # noqa: E402
import version as V  # noqa: E402


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_current_version_is_m26_10_24_and_has_changelog():
    check(V.APP_VERSION == "M26.10.24", V.APP_VERSION)
    check("M26.10.24" in V.CHANGELOG and V.CHANGELOG["M26.10.24"]["changes"], "журнал для текущей версии есть")


def test_m_version_is_newer_than_old_dated_versions():
    check(U.is_newer("M26.10.24", "2026.10.2301"), "M26.10.24 новее 2026.10.2301")
    check(U.is_newer("M26.10.24", "2026.10.1231"), "новее старых выпусков")
    check(not U.is_newer("2026.10.2301", "M26.10.24"), "старый номер не предлагаем вместо нового")


def test_several_releases_per_day_and_next_day_order():
    check(U.is_newer("M26.10.24.2", "M26.10.24"), "второй выпуск за день новее первого")
    check(U.is_newer("M26.10.25", "M26.10.24.2"), "следующий день новее всех за предыдущий")
    check(not U.is_newer("M26.10.24", "M26.10.24"), "та же версия — не предлагаем")


def test_github_tags_in_new_scheme_are_recognised():
    check(U.version_of("vM26.10.24") == "M26.10.24", U.version_of("vM26.10.24"))
    check(U.version_of("M26.10.24.2") == "M26.10.24.2")
    check(U.version_of("release-M26") is None, "мусор не принимаем")
    check(U.version_of("v2026.10.1231") == "2026.10.1231", "старые теги работают")


def test_changelog_file_is_generated_from_version_py():
    md = open(_os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    check("**M26.10.24**" in md and "## M26.10.24" in md, "CHANGELOG.md обновлён")
