# Mico AI на GitHub

Репозиторий: https://github.com/Serdzh29/Mico-AI

| Что | Где лежит | Как публикуется |
|---|---|---|
| Программа (Python) | корень репозитория | тег `v…` запускает `release.yml`: сборка Mico.exe и релиз |
| Сайт | `cloud/public/` | `pages.yml`: GitHub Pages, https://serdzh29.github.io/Mico-AI/ |
| Шлюз Mico Cloud | `cloud/src/worker.js` | `deploy-worker.yml`: `wrangler deploy` в Cloudflare |
| Ключи Groq, Gemini, NVIDIA | секреты воркера в Cloudflare | не хранятся в репозитории |

## Первый запуск
1. Settings → Pages → Source: **GitHub Actions**.
2. Settings → Secrets and variables → Actions → New repository secret:
   `CLOUDFLARE_API_TOKEN` (шаблон «Edit Cloudflare Workers») и `CLOUDFLARE_ACCOUNT_ID`.
3. Push в `main`: сайт и шлюз публикуются сами.
4. Новая версия программы: поднимите номер в `setup/version.py`, `cloud/public/config.js` и `cloud/public/version.json`, затем
   `git tag v2514 && git push origin v2514`. Mico.exe появится в Releases, ссылка на сайте всегда ведёт на последний релиз.

## Адреса
- Сайт и номер версии: `SITE_URL` в `setup/version.py`.
- Шлюз облака: `CLOUD_URL` в `setup/version.py` (остаётся на workers.dev, GitHub Pages не умеет серверный код).
- Старые установки проверяют версию на workers.dev: пока они есть, воркер продолжает отдавать `cloud/public/` (`assets` в `wrangler.jsonc`).
