import datetime

print(datetime.datetime.now(datetime.timezone.utc))
print(datetime.datetime.now())
print(datetime.datetime.now() + datetime.timedelta(days=1))
print(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
