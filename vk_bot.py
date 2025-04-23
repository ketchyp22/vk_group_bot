#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import vk_api
import time
import random
import json
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vk_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("VK_Bot")

class VKInviteBot:
    def __init__(self):
        """Инициализация бота с параметрами из переменных окружения"""
        self.load_config()
        
        # Авторизация в ВК
        try:
            self.vk_session = vk_api.VkApi(token=self.config["access_token"])
            self.vk = self.vk_session.get_api()
            logger.info("Успешная авторизация в VK API")
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            exit(1)
            
        # Статистика и состояние
        self.stats_file = "stats.json"
        self.load_stats()
        
    def load_config(self):
        """Загрузка настроек из переменных окружения"""
        try:
            # Функция для безопасного преобразования в целое число
            def safe_int(value, default=0):
                try:
                    return int(value)
                except (ValueError, TypeError):
                    # Если значение является строкой и начинается с "id" или содержит имя пользователя
                    if isinstance(value, str):
                        # Попытка извлечь числовой ID группы, если он в формате club12345678
                        if value.startswith(('club', 'public')):
                            try:
                                return int(value[5:]) # Убираем 'club' или 'public'
                            except ValueError:
                                pass
                    logger.warning(f"Не удалось преобразовать '{value}' в целое число, используется значение по умолчанию {default}")
                    return default

            # Получение конфигурации из переменных окружения
            self.config = {
                "access_token": os.getenv("VK_ACCESS_TOKEN"),
                "target_group_id": os.getenv("TARGET_GROUP_ID"),  # Оставляем строку для обработки
                "your_group_id": os.getenv("YOUR_GROUP_ID"),      # Оставляем строку для обработки
                "max_invites_per_day": safe_int(os.getenv("MAX_INVITES_PER_DAY"), 20),
                "delay_between_invites": {     
                    "min": safe_int(os.getenv("MIN_DELAY"), 120),   # Умеренная задержка (2 минуты)
                    "max": safe_int(os.getenv("MAX_DELAY"), 240)    # Умеренная задержка (4 минуты)
                },
                "filters": {
                    "age": {
                        "enabled": os.getenv("FILTER_AGE_ENABLED", "False").lower() == "true",
                        "min": safe_int(os.getenv("FILTER_AGE_MIN"), 18),
                        "max": safe_int(os.getenv("FILTER_AGE_MAX"), 50)
                    },
                    "sex": {
                        "enabled": os.getenv("FILTER_SEX_ENABLED", "False").lower() == "true",
                        "value": safe_int(os.getenv("FILTER_SEX_VALUE"), 0)
                    },
                    "city_id": {
                        "enabled": os.getenv("FILTER_CITY_ENABLED", "False").lower() == "true",
                        "value": safe_int(os.getenv("FILTER_CITY_VALUE"), 1)
                    },
                    "has_photo": {
                        "enabled": os.getenv("FILTER_PHOTO_ENABLED", "False").lower() == "true"
                    },
                    "last_seen_days": {
                        "enabled": os.getenv("FILTER_LAST_SEEN_ENABLED", "True").lower() == "true",
                        "value": safe_int(os.getenv("FILTER_LAST_SEEN_DAYS"), 30)
                    }
                }
            }
            
            # Обработка ID группы, позволяем использовать короткое имя или полный URL
            target_group = self.config["target_group_id"]
            your_group = self.config["your_group_id"]
            
            logger.info(f"Исходное значение TARGET_GROUP_ID: {target_group}")
            logger.info(f"Исходное значение YOUR_GROUP_ID: {your_group}")
            
            # Проверка обязательных параметров
            if not self.config["access_token"]:
                logger.error("Не задан VK_ACCESS_TOKEN в переменных окружения")
                exit(1)
                
            logger.info("Конфигурация успешно загружена из переменных окружения")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            import traceback
            logger.error(traceback.format_exc())
            exit(1)
    
    def get_group_id(self, group_identifier):
        """Получение числового ID группы по короткому имени или строковому ID"""
        try:
            # Если это уже число, просто возвращаем его
            try:
                return int(group_identifier)
            except (ValueError, TypeError):
                pass
                
            # Небольшая задержка перед API запросом
            time.sleep(1)
            
            # Пытаемся получить ID по короткому имени
            response = self.vk.groups.getById(group_id=group_identifier)
            if response and len(response) > 0:
                return response[0]['id']
                
            logger.warning(f"Не удалось получить ID группы для '{group_identifier}', используется как есть")
            return group_identifier
            
        except Exception as e:
            logger.error(f"Ошибка получения ID группы: {e}")
            return group_identifier
    
    def load_stats(self):
        """Загрузка статистики и состояния бота"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
            else:
                self.stats = {
                    "total_invites_sent": 0,
                    "invites_today": 0,
                    "last_invite_date": None,
                    "processed_users": [],
                    "users_with_privacy_restrictions": [],
                    "last_activity_time": None
                }
                self.save_stats()
                
            # Проверка наличия поля для пользователей с ограничениями приватности
            if "users_with_privacy_restrictions" not in self.stats:
                self.stats["users_with_privacy_restrictions"] = []
                self.save_stats()
                
        except Exception as e:
            logger.error(f"Ошибка загрузки статистики: {e}")
            self.stats = {
                "total_invites_sent": 0,
                "invites_today": 0,
                "last_invite_date": None,
                "processed_users": [],
                "users_with_privacy_restrictions": [],
                "last_activity_time": None
            }
    
    def save_stats(self):
        """Сохранение статистики и состояния бота"""
        try:
            # Обновляем время последней активности
            self.stats["last_activity_time"] = datetime.now().isoformat()
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики: {e}")
    
    def reset_daily_counter(self):
        """Сброс дневного счетчика приглашений"""
        today = datetime.now().strftime("%Y-%m-%d")
        last_date = self.stats["last_invite_date"]
        
        if last_date and last_date != today:
            logger.info("Сброс дневного счетчика приглашений")
            self.stats["invites_today"] = 0
            self.save_stats()
    
    def get_group_members(self, group_id, count=1000):
        """Получение списка участников группы"""
        try:
            # Получаем числовой ID группы, если передано короткое имя
            actual_group_id = self.get_group_id(group_id)
            logger.info(f"Получение участников группы: {group_id} (ID: {actual_group_id})")
            
            members = []
            offset = 0
            
            while True:
                # Небольшая задержка между запросами
                time.sleep(1)
                
                response = self.vk.groups.getMembers(
                    group_id=actual_group_id,
                    offset=offset,
                    count=1000,
                    fields="sex,bdate,city,last_seen,has_photo"
                )
                
                batch = response["items"]
                if not batch:
                    break
                    
                members.extend(batch)
                offset += 1000
                
                if offset >= count:
                    break
                    
                # Задержка между запросами для соблюдения ограничений API
                time.sleep(2)
                
            logger.info(f"Получено {len(members)} участников из группы {group_id}")
            
            # Перемешиваем список пользователей для более естественного поведения
            random.shuffle(members)
            
            return members
        except Exception as e:
            logger.error(f"Ошибка получения участников группы: {e}")
            
            # Если получили ошибку, сделаем паузу и попробуем снова
            if "captcha" in str(e).lower():
                logger.warning("Обнаружена капча, делаем паузу в 15 минут...")
                time.sleep(900)  # 15 минут
            
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def filter_users(self, users):
        """Фильтрация пользователей согласно настройкам"""
        filtered_users = []
        filters = self.config["filters"]
        
        for user in users:
            # Пропускаем уже обработанных пользователей
            if user["id"] in self.stats["processed_users"]:
                continue
                
            # Пропускаем пользователей с известными ограничениями приватности
            if user["id"] in self.stats["users_with_privacy_restrictions"]:
                continue
                
            # Проверка, не является ли пользователь уже участником нашей группы
            try:
                time.sleep(0.5)  # Небольшая задержка
                
                actual_group_id = self.get_group_id(self.config["your_group_id"])
                is_member = self.vk.groups.isMember(
                    group_id=actual_group_id,
                    user_id=user["id"]
                )
                
                if is_member:
                    continue
            except Exception as e:
                if "captcha" in str(e).lower():
                    logger.warning("Обнаружена капча при проверке участия, делаем паузу в 10 минут...")
                    time.sleep(600)  # 10 минут
                # При ошибке пропускаем пользователя
                continue
                
            is_suitable = True
            
            # Фильтр по последней активности
            if filters["last_seen_days"]["enabled"] and "last_seen" in user:
                last_seen_time = user["last_seen"]["time"]
                last_seen_date = datetime.fromtimestamp(last_seen_time)
                days_ago = (datetime.now() - last_seen_date).days
                
                if days_ago > filters["last_seen_days"]["value"]:
                    is_suitable = False
                    
            # Фильтр по полу
            if filters["sex"]["enabled"] and filters["sex"]["value"] != 0:
                if "sex" not in user or user["sex"] != filters["sex"]["value"]:
                    is_suitable = False
                    
            # Фильтр по городу
            if filters["city_id"]["enabled"]:
                if "city" not in user or user["city"]["id"] != filters["city_id"]["value"]:
                    is_suitable = False
                    
            # Фильтр по наличию фото
            if filters["has_photo"]["enabled"]:
                if "has_photo" not in user or user["has_photo"] != 1:
                    is_suitable = False
                    
            # Фильтр по возрасту (если указана дата рождения)
            if filters["age"]["enabled"] and "bdate" in user:
                try:
                    bdate = user["bdate"]
                    if len(bdate.split(".")) == 3:  # Формат DD.MM.YYYY
                        birth_date = datetime.strptime(bdate, "%d.%m.%Y")
                        age = (datetime.now() - birth_date).days // 365
                        
                        if age < filters["age"]["min"] or age > filters["age"]["max"]:
                            is_suitable = False
                except:
                    # При ошибке парсинга даты рождения пропускаем этот фильтр
                    pass
                    
            if is_suitable:
                filtered_users.append(user)
                
        logger.info(f"Отфильтровано {len(filtered_users)} подходящих пользователей из {len(users)}")
        return filtered_users
    
    def invite_user(self, user_id):
        """Отправка приглашения пользователю"""
        try:
            # Небольшая задержка перед приглашением
            time.sleep(random.uniform(1, 3))
            
            actual_group_id = self.get_group_id(self.config["your_group_id"])
            result = self.vk.groups.invite(
                group_id=actual_group_id,
                user_id=user_id
            )
            
            # Обновление статистики
            today = datetime.now().strftime("%Y-%m-%d")
            self.stats["total_invites_sent"] += 1
            self.stats["invites_today"] += 1
            self.stats["last_invite_date"] = today
            self.stats["processed_users"].append(user_id)
            self.save_stats()
            
            logger.info(f"Успешно отправлено приглашение пользователю ID{user_id}")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            
            if "captcha" in error_msg:
                logger.warning(f"Капча при отправке приглашения пользователю ID{user_id}. Делаем паузу...")
                # Пауза при обнаружении капчи
                time.sleep(900)  # 15 минут
            elif "permission to add" in error_msg or "can't add this user" in error_msg or "user disabled invites" in error_msg or "access denied" in error_msg:
                # Пользователь ограничил возможность приглашения в группы
                logger.info(f"Пользователь ID{user_id} ограничил возможность приглашения в группы")
                # Добавляем его в список пользователей с ограничениями приватности
                self.stats["users_with_privacy_restrictions"].append(user_id)
                self.stats["processed_users"].append(user_id)
                self.save_stats()
            else:
                logger.error(f"Ошибка при отправке приглашения пользователю ID{user_id}: {e}")
                # Добавляем в обработанные, чтобы не пытаться снова
                self.stats["processed_users"].append(user_id)
                self.save_stats()
                
            return False
    
    def run(self):
        """Основная функция работы бота"""
        logger.info("Запуск бота для приглашения пользователей")
        
        # Сброс дневного счетчика при необходимости
        self.reset_daily_counter()
        
        # Проверка лимита на сегодня
        if self.stats["invites_today"] >= self.config["max_invites_per_day"]:
            logger.warning(f"Достигнут дневной лимит приглашений ({self.config['max_invites_per_day']}). Бот будет остановлен.")
            return
            
        # Получение участников целевой группы
        target_users = self.get_group_members(self.config["target_group_id"])
        
        if not target_users:
            logger.error("Не удалось получить пользователей целевой группы. Проверьте ID группы.")
            return
            
        # Фильтрация подходящих пользователей
        filtered_users = self.filter_users(target_users)
        
        if not filtered_users:
            logger.warning("Не найдено подходящих пользователей для приглашения.")
            return
        
        # Отправка приглашений с учетом лимитов
        invites_left = self.config["max_invites_per_day"] - self.stats["invites_today"]
        
        # Ограничение для одного запуска
        max_batch = min(invites_left, 10)  # Максимум 10 приглашений за один запуск
        invites_count = min(len(filtered_users), max_batch)
        
        logger.info(f"Планируется отправить {invites_count} приглашений")
        
        # Счетчики для статистики
        success_count = 0
        privacy_restricted_count = 0
        error_count = 0
        
        for i in range(invites_count):
            user = filtered_users[i]
            
            # Отправка приглашения
            try:
                result = self.invite_user(user["id"])
                if result:
                    success_count += 1
                else:
                    # Проверка, не был ли пользователь добавлен в список с ограничениями приватности
                    if user["id"] in self.stats["users_with_privacy_restrictions"]:
                        privacy_restricted_count += 1
                    else:
                        error_count += 1
            except Exception as e:
                logger.error(f"Непредвиденная ошибка при обработке пользователя ID{user['id']}: {e}")
                error_count += 1
            
            # Задержка между приглашениями
            if i < invites_count - 1:
                delay = random.randint(
                    self.config["delay_between_invites"]["min"],
                    self.config["delay_between_invites"]["max"]
                )
                logger.info(f"Ожидание {delay} секунд ({delay/60:.1f} минут) перед следующим приглашением...")
                time.sleep(delay)
        
        # Итоговая статистика
        logger.info(f"Успешно отправлено: {success_count} приглашений")
        logger.info(f"Пользователей с ограничениями приватности: {privacy_restricted_count}")
        logger.info(f"Ошибок: {error_count}")
        logger.info("Работа бота завершена")
        
        # Сколько пользователей всего в базе с ограничениями приватности
        logger.info(f"Всего пользователей с ограничениями приватности в базе: {len(self.stats['users_with_privacy_restrictions'])}")

def main():
    """Точка входа в программу"""
    logger.info("=" * 50)
    logger.info("Запуск программы")
    
    try:
        bot = VKInviteBot()
        bot.run()
        
        # Для Railway: запуск по расписанию с интервалом
        while True:
            # Интервал между запусками (4-6 часов)
            sleep_hours = random.uniform(4.0, 6.0)
            logger.info(f"Ожидание следующего запуска ({sleep_hours:.2f} часов)...")
            time.sleep(sleep_hours * 60 * 60)
            logger.info("Запуск нового цикла")
            bot = VKInviteBot()
            bot.run()
    except KeyboardInterrupt:
        logger.info("Программа остановлена пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
