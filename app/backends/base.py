from abc import ABC, abstractmethod


class AuthBackend(ABC):
    @abstractmethod
    def login():
        pass

    @abstractmethod
    def logout():
        pass

    @abstractmethod
    def authenticate_request():
        pass
