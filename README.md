# VK Group Invitation Bot

Бот для автоматизированного приглашения пользователей из одной группы ВКонтакте в другую с учетом всех ограничений платформы.

## Особенности

- Парсинг участников указанной группы ВКонтакте
- Фильтрация пользователей по различным критериям (возраст, пол, город, активность)
- Соблюдение лимитов на количество приглашений
- Случайные задержки между приглашениями для имитации человеческого поведения
- Сохранение статистики и списка обработанных пользователей
- Подробное логирование всех действий

## Настройка

1. Установите зависимости:
```
pip install -r requirements.txt
```

2. Создайте и заполните файл `.env` по шаблону:
```
VK_ACCESS_TOKEN=ваш_токен_доступа
TARGET_GROUP_ID=12345678
YOUR_GROUP_ID=87654321
MAX_INVITES_PER_DAY=20
MIN_DELAY=60
MAX_DELAY=180
```

## Запуск локально

```
python vk_bot.py
```

## Деплой на Railway.app

1. Создайте аккаунт на [Railway.app](https://railway.app/)
2. Создайте новый проект из GitHub репозитория
3. Добавьте все переменные окружения из файла `.env` в настройках проекта
4. Railway автоматически развернет ваш проект и запустит бота

## Безопасность

Бот настроен с учетом всех ограничений API ВКонтакте:
- Лимит на количество приглашений в день (по умолчанию 20)
- Случайные задержки между действиями (от 1 до 3 минут)
- Автоматическая пауза между запусками (3 часа)

## Важные примечания

- Данный бот создан в образовательных целях
- Использование бота может противоречить правилам ВКонтакте
- Автор не несет ответственности за возможную блокировку аккаунта или группы
- При частом использовании рекомендуется увеличить задержки между приглашениями
