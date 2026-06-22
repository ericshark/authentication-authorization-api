from argon2 import PasswordHasher

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(hashed_password: str, plain_password: str) -> None:
    password_hasher.verify(hashed_password, plain_password)
