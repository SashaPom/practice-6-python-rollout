# Практична робота 6 · CI/CD Python-сервісу

Сервіс має два маршрути. `/health` повертає стан, а `/version` — версію, яку передано під час збірки. Для образів CI значенням версії є повний SHA коміту. Сервіс працює в контейнері під UID 10001.

## Локальний запуск

Потрібні Python 3.12, Docker і Docker Compose.

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-test.txt
docker build --build-arg APP_VERSION=local-v1 -t practice6-service:local .
docker compose up -d --wait --wait-timeout 25
```

`APP_IMAGE` задає образ, `APP_PORT` — внутрішній порт, `HOST_PORT` — локальний порт. Сервіс читає `APP_VERSION` і `APP_HEALTH_MODE` з оточення контейнера. Режим `ok` відповідає HTTP 200, а режим `down` повертає HTTP 503.

## Перевірка

```bash
pytest -q tests
pytest -q infra --hosts="docker://$(docker compose ps -q service)"
python ci/probe.py http://127.0.0.1:8098 local-v1
docker compose logs --no-color service
```

Тест API перевіряє HTTP-статуси й JSON. Testinfra перевіряє файли, процес PID 1, порт і UID цього процесу. Команда `ci/probe.py` закінчується помилкою, якщо не збігається статус або тіло хоча б однієї відповіді.

## Автоматична доставка та експерименти

Для pull request до `main` тести й збірка виконуються окремими завданнями. Після злиття запуск для `main` передає той самий зібраний образ із build до deploy через артефакт. Linux VM запускає Compose, Testinfra і HTTP-перевірку. Здоровий образ отримує тег `stable`; попередній образ фіксується за digest перед підміною контейнера. У разі збою конвеєр відновлює цей digest, повторно перевіряє `/health` і `/version` та завершує невдалий прогін із кодом 1.

Усі запуски зберігають діагностику завдань, які стартували. У вкладці Actions доступні JUnit-звіти, лог збірки, а для розгортань — також Testinfra, HTTP, стани Compose і логи контейнера. Логи кандидата зберігаються перед його заміною.

На гілці `lab/broken-pytest` навмисно змінено очікуваний статус у тесті `/version`. На гілці `lab/broken-health` змінено вбудований у Dockerfile режим на `down`. Запускайте експеримент зі зламаним health після успішного прогону `main`, щоб тег `stable` уже існував.

```bash
gh workflow run ci-cd.yml --ref lab/broken-pytest
gh workflow run ci-cd.yml --ref lab/broken-health
```

## Ручне повернення образу та завершення роботи

Підставте раніше перевірений образ з тегом або digest і його версію. Для приватного GHCR спочатку виконайте вхід із дозволом читання пакета.

```bash
read -r -p "Previous image reference: " PREVIOUS_IMAGE
read -r -p "Previous version: " PREVIOUS_VERSION
export APP_IMAGE="$PREVIOUS_IMAGE"
docker compose pull service
docker compose up -d --force-recreate --wait --wait-timeout 25
python ci/probe.py http://127.0.0.1:8098 "$PREVIOUS_VERSION"
docker compose down
```

## Навчальне розміщення

Для роботи використав тимчасові Linux VM GitHub Actions. Після завершення VM зупиняється, а перевірена версія зберігається в GHCR. На IaaS цей самий Compose можна запустити на постійній Linux VM, де команда оновлюватиме ОС, Docker і застосунок. На PaaS можна передати контейнер керованому сервісу, де провайдер оновлюватиме середовище, а команда відповідатиме за образ і налаштування. Витрати можуть створювати час обчислень, диски, місце в реєстрі та вихідний трафік.
