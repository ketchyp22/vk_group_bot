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
            self.config = {
                "access_token": os.getenv("VK_ACCESS_TOKEN"),
                "target_group_id": int(os.getenv("TARGET_GROUP_ID")),
                "your_group_id": int(os.getenv("YOUR_GROUP_ID")),
                "max_invites_per_day": int(os.getenv("MAX_INVITES_PER_DAY", "20")),
                "delay_between_invites": {     
                    "min": int(os.getenv("MIN_DELAY", "60")),
                    "max": int(os.getenv("MAX_DELAY", "180"))
                },
                "filters": {
                    "age": {
                        "enabled": os.getenv("FILTER_AGE_ENABLED", "False").lower() == "true",
                        "min": int(os.getenv("FILTER_AGE_MIN", "18")),
                        "max": int(os.getenv("FILTER_AGE_MAX", "50"))
                    },
                    "sex": {
                        "enabled": os.getenv("FILTER_SEX_ENABLED", "False").lower() == "true",
                        "value": int(os.getenv("FILTER_SEX_VALUE", "0"))
                    },
                    "city_id": {
                        "enabled": os.getenv("FILTER_CITY_ENABLED", "False").lower() == "true",
                        "value": int(os.getenv("FILTER_CITY_VALUE", "1"))
                    },
                    "has_photo": {
                        "enabled": os.getenv("FILTER_PHOTO_ENABLED", "False").lower() == "true"
                    },
                    "last_seen_days": {
                        "enabled": os.getenv("FILTER_LAST_SEEN_ENABLED", "True").lower() == "true",
                        "value": int(os.getenv("FILTER_LAST_SEEN_DAYS", "30"))
                    }
                }
            }
            
            # Проверка обязательных параметров
            if not self.config["access_token"]:
                logger.error("Не задан VK_ACCESS_TOKEN в переменных окружения")
                exit(1)
                
            logger.info("Конфигурация успешно загружена из переменных окружения")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            exit(1)
    
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
                    "processed_users": []
                }
                self.save_stats()
        except Exception as e:
            logger.error(f"Ошибка загрузки статистики: {e}")
            self.stats = {
                "total_invites_sent": 0,
                "invites_today": 0,
                "last_invite_date": None,
                "processed_users": []
            }
    
    def save_stats(self):
        """Сохранение статистики и состояния бота"""
        try:
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
            members = []
            offset = 0
            
            while True:
                response = self.vk.groups.getMembers(
                    group_id=group_id,
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
                time.sleep(0.4)
                
            logger.info(f"Получено {len(members)} участников из группы ID{group_id}")
            return members
        except Exception as e:
            logger.error(f"Ошибка получения участников группы: {e}")
            return []
    
    def filter_users(self, users):
        """Фильтрация пользователей согласно настройкам"""
        filtered_users = []
        filters = self.config["filters"]
        
        for user in users:
            # Пропускаем уже обработанных пользователей
            if user["id"] in self.stats["processed_users"]:
                continue
                
            # Проверка, не является ли пользователь уже участником нашей группы
            try:
                is_member = self.vk.groups.isMember(
                    group_id=self.config["your_group_id"],
                    user_id=user["id"]
                )
                if is_member:
                    continue
            except:
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
            self.vk.groups.invite(
                group_id=self.config["your_group_id"],
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
        
        # Фильтрация подходящих пользователей
        filtered_users = self.filter_users(target_users)
        
        # Отправка приглашений с учетом лимитов
        invites_left = self.config["max_invites_per_day"] - self.stats["invites_today"]
        invites_count = min(len(filtered_users), invites_left)
        
        logger.info(f"Планируется отправить {invites_count} приглашений")
        
        for i in range(invites_count):
            user = filtered_users[i]
            
            # Отправка приглашения
            success = self.invite_user(user["id"])
            
            # Задержка между приглашениями
            if i < invites_count - 1 and success:
                delay = random.randint(
                    self.config["delay_between_invites"]["min"],
                    self.config["delay_between_invites"]["max"]
                )
                logger.info(f"Ожидание {delay} секунд перед следующим приглашением...")
                time.sleep(delay)
        
        logger.info("Работа бота завершена")

def main():
    """Точка входа в программу"""
    logger.info("=" * 50)
    logger.info("Запуск программы")
    
    bot = VKInviteBot()
    bot.run()
    
    # Для Railway: запуск по расписанию с интервалом
    while True:
        logger.info("Ожидание следующего запуска (3 часа)...")
        time.sleep(3 * 60 * 60)  # 3 часа
        logger.info("Запуск нового цикла")
        bot = VKInviteBot()
        bot.run()

if __name__ == "__main__":
    main()
