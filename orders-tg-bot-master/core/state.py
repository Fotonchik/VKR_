# core/state.py

import time


class StateManager:
    """
    Простейший FSM-хранилище состояний пользователей.
    Хранит:
      - текущее состояние
      - временные данные
      - время последнего действия
    """

    TIMEOUT = 600  # 10 минут

    def __init__(self):
        self._storage = {}

    def set(self, user_id: int, state: str, data: dict):
        self._storage[user_id] = {
            "state": state,
            "data": data,
            "timestamp": time.time()
        }

    def get(self, user_id: int) -> dict:
        item = self._storage.get(user_id)
        if not item:
            return {}

        # таймаут
        if time.time() - item["timestamp"] > self.TIMEOUT:
            self.clear(user_id)
            return {}

        return item["data"]

    def get_state(self, user_id: int) -> str | None:
        item = self._storage.get(user_id)
        if not item:
            return None

        if time.time() - item["timestamp"] > self.TIMEOUT:
            self.clear(user_id)
            return None

        return item["state"]

    def clear(self, user_id: int):
        self._storage.pop(user_id, None)

    def has_state(self, user_id: int) -> bool:
        return self.get_state(user_id) is not None
