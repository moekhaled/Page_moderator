import asyncio

from app.create_tables import init_db


if __name__ == "__main__":
    asyncio.run(init_db())
