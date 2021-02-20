# SEO tools by m0r9un

Репозиторий с небольшими скриптами для автоматизации SEO процессов.

## Serpstat

key_stats.py - скрипт для получения ТОП по списку запросов, проверки позиций, файла импорта для KeyAssort. [github key_stats.py](https://github.com/m0r9un/seo-tools/blob/main/serpstat/key_stats.py)

YOUR_TOKEN нужно поменять на ваш token serpstat api.

Код работает на Python 3.7 на Serpstat API v3 (пока еще).

* Сохраняем файл key_stats.py в одной папке с keywords.txt в котором списком через enter записаны ключи.
* Выполняем программу через: python3 ./key_stats.py -k "keywords.txt" -s g_ua -d "flatfy.ua, lun.ua" -i -t 10
* python3 может быть еще python или py в зависимости от OS и способа установки Python.
* "flatfy.ua, lun.ua" - список доменов на проверку в ТОП.

Описание остальных параметров есть в файле.
