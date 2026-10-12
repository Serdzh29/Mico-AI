"""Генерирует CHANGELOG.md из version.py. Версии и изменения правим только в version.py."""
import os
import version


def main():
    lines = ["# История изменений Mico", "",
             f"Текущая версия: **{version.APP_VERSION}**. Этот файл создан из `version.py` — не правь его вручную.", ""]
    for ver in sorted(version.CHANGELOG, key=version._vt, reverse=True):
        lines.append(f"## {ver}")
        lines += [f"- {c}" for c in version.CHANGELOG[ver]["changes"]]
        lines.append("")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CHANGELOG.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("written:", path)


if __name__ == "__main__":
    main()
