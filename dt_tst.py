import datetime
import secrets

import pyotp

print(datetime.datetime.now(datetime.timezone.utc))
print(datetime.datetime.now())
print(datetime.datetime.now() + datetime.timedelta(days=1))
print(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
secret = "EEOTMVB4EZWBGWXTTR322G4O3ZCKF3FF"
totp = pyotp.TOTP(secret)
print(totp.now())  # this pr
print(totp.verify("529206"))

print(secrets.token_hex(4))
print(len(secrets.token_hex(4)))
temp = ""
backup_codes = [f"{secrets.token_hex(4)}-{secrets.token_hex(4)}" for x in range(10)]
print({"bc": backup_codes})
x = "5"
print(x.encode())
