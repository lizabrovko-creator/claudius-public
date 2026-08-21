# claudius — інструменти Upstars для Claude Code

Плагін `upstars` для [Claude Code](https://code.claude.com). Наразі містить
`twbx-lint` — лінтер і «ремонтник» воркбуків Tableau (`.twbx`) за стайлгайдом
Upstars.

**[Документація та приклади →](https://lizabrovko-creator.github.io/claudius-public/)**

## Що робить `twbx-lint`

Бере `.twbx`, клонує його в `results/` під іменем з міткою часу, приводить у
відповідність до стайлгайду — типографіка, кольори, макет, поведінка фільтрів —
і **доводить, що результат відкривається в Tableau Desktop**. Оригінал у
`dummy/` лишається байт-у-байт незмінним: за це відповідає окремий хук, який
блокує будь-який запис туди.

Скил не звітує про успіх, поки не виконано дві умови одночасно: `validate`
показав `PASS` на запакованому файлі, і `open-verify` показав `OK`.

## Вимоги

| Що | Навіщо |
| --- | --- |
| **macOS** | `open-verify` шукає Tableau Desktop у `/Applications`. На Windows і Linux повертає `SKIP`, а `SKIP` не є успіхом — тобто завершити роботу там неможливо |
| **Tableau Desktop** | без нього немає фінальної перевірки відкриття |
| **Python 3.9+** | `from __future__ import annotations` відкладає перевірку типів у рантаймі, тому `X \| None` не вимагає 3.10 — перевірено на 3.9.25 |
| **xmllint** | macOS має його з коробки; на Linux це `libxml2-utils` |
| **jq** | потрібен хуку `run-tests-on-change.sh`, який перезапускає тести при зміні коду скіла — без нього хук тепер падає гучно (exit 2), а не мовчки |

Перевірити оточення: `python3 plugins/upstars/skills/twbx-lint/scripts/twbx_tool.py doctor`

Команда `doctor --fix` створює відсутні теки `dummy/` і `results/`.

## Встановлення

```
/plugin marketplace add lizabrovko-creator/claudius-public
/plugin install upstars@claudius
```

Якщо після встановлення Claude Code напише `Run /reload-plugins to activate.` —
виконай `/reload-plugins`.

Оновлення пізніше: `/plugin marketplace update claudius`

<details>
<summary>Альтернатива: без маркетплейса</summary>

```bash
git clone https://github.com/lizabrovko-creator/claudius-public.git
cd claudius
claude --plugin-dir ./plugins/upstars
```

Так плагін завантажується лише на одну сесію — зручно, щоб спробувати.
</details>

## Як користуватись

Поклади воркбук у `dummy/` і виклич:

```
/upstars:twbx-lint dummy/my-dashboard.twbx
```

Без аргументу скил візьме найновіший `.twbx` із `dummy/`.

Результат з'явиться в `results/` з міткою часу в імені. У кінці скил показує
короткий звіт: що виправлено, вердикт щодо кожного розділу чеклиста, що лишилось
невиправленим і чому, рядок валідації, рядок відкриття в Tableau, і що саме
треба підтвердити очима у відкритому вікні.

## Розробка

Тести не запускаються під час звичайної роботи. Вони спрацьовують лише коли
змінюються **вихідники самого скила**.

```
/upstars:twbx-lint-test          # усі тести
/upstars:twbx-lint-test -k guards
```

Або напряму:

```bash
plugins/upstars/skills/twbx-lint/tests/run.sh
```

Коди виходу: `0` чисто · `1` тести впали · `3` зламана структура скила.

Три рівні перевірок:

| Рівень | Що | Ціна | Запуск |
| --- | --- | --- | --- |
| 1 · структура | `claude plugin validate --strict` | ~0.3 с | автоматично |
| 2 · логіка | `pytest` | ~2 с | автоматично |
| 3 · поведінка моделі | LLM-евали | години, платно | лише вручну |

Рівень 3 живе у приватному репозиторії разом із тестовими воркбуками й запускається супроводжувачами скила. Коротко:
запускати лише після переписування **прози** `SKILL.md`, не після правок коду.

## Ліцензія

MIT — див. [LICENSE](LICENSE).
