import os

from pydantic import BaseModel
class env_variables(BaseModel):
    secret: str = os.getenv("RANDOM_SECRET", "PROOOOOOOD!!!!!!!!!11!!1!")
    server_address: str = os.getenv("SERVER_ADDRESS", "0.0.0.0:8080")
    database_url: str = os.getenv("POSTGRES_CONN", "f'postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database_name}'")
    postgres_username: str = os.getenv("POSTGRES_USERNAME", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = os.getenv("POSTGRES_PORT", 5432)
    postgres_database: str = os.getenv("POSTGRES_DATABASE", "prod2025")
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = os.getenv("REDIS_PORT", 6379)
    antifraud_address: int = os.getenv("ANTIFRAUD_ADDRESS", "localhost:9090")



