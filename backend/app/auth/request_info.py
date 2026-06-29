from fastapi import Request
from user_agents import parse


def get_ip_address(request: Request) -> str:
    ip_address = (
        request.headers.get("X-Forwarded-For")
        or (request.client.host if request.client else None)
        or "unknown"
    )
    return ip_address.split(",")[0].strip()


def get_device_name(request: Request) -> str:
    ua = parse(request.headers.get("User-Agent", ""))
    device_name = f"{ua.browser.family} on {ua.os.family}"
    return device_name
