"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure Blob Storage
    azure_storage_account_url: str = ""
    azure_storage_connection_string: str = ""

    # Container names (match existing pipeline)
    bronze_container: str = "bronze"
    gold_container: str = "gold"
    metadata_container: str = "ui-metadata"

    # Entra ID / Azure AD
    azure_tenant_id: str = ""
    azure_client_id: str = ""  # Backend app registration client ID
    azure_authority: str = ""

    # CORS
    frontend_origin: str = "http://localhost:3000"

    # Upload limits
    max_upload_size_mb: int = 20
    allowed_extensions: str = "jpg,jpeg,png"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def authority_url(self) -> str:
        if self.azure_authority:
            return self.azure_authority
        return f"https://login.microsoftonline.com/{self.azure_tenant_id}"

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {ext.strip().lower() for ext in self.allowed_extensions.split(",")}

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()
