from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = 'CompDDL API'
    api_v1_str: str = '/api'

    mysql_user: str = 'root'
    mysql_password: str = '12345678'
    mysql_host: str = 'localhost'
    mysql_port: int = 3306
    mysql_db: str = 'compddl'

    openai_api_key: str = ''
    openai_default_model: str = 'gpt-4.1-mini'
    research_runtime_mode: str = 'mock'
    research_runtime_tracing_enabled: bool = True
    research_runtime_session_db: str = ''

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f'mysql+pymysql://{self.mysql_user}:{self.mysql_password}'
            f'@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4'
        )

    class Config:
        env_file = '.env'
        extra = 'ignore'


settings = Settings()
