from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------
# Canales estándar — el "diccionario" de homologación
# ---------------------------------------------------
class ChannelEnum(str, Enum):
    FACEBOOK = "FACEBOOK"
    GOOGLE_ADS = "GOOGLE_ADS"
    INSTAGRAM = "INSTAGRAM"
    EMAIL = "EMAIL"
    ORGANIC = "ORGANIC"


CHANNEL_MAP: dict[str, ChannelEnum] = {
    # Facebook
    "facebook": ChannelEnum.FACEBOOK,
    "fb": ChannelEnum.FACEBOOK,
    "fb ads": ChannelEnum.FACEBOOK,
    "fb_ads": ChannelEnum.FACEBOOK,
    "facebook ads": ChannelEnum.FACEBOOK,
    "facebook_ads": ChannelEnum.FACEBOOK,
    # Google
    "google": ChannelEnum.GOOGLE_ADS,
    "google ads": ChannelEnum.GOOGLE_ADS,
    "google_ads": ChannelEnum.GOOGLE_ADS,
    "googleads": ChannelEnum.GOOGLE_ADS,
    # Instagram
    "instagram": ChannelEnum.INSTAGRAM,
    "ig": ChannelEnum.INSTAGRAM,
    "ig ads": ChannelEnum.INSTAGRAM,
    # Email
    "email": ChannelEnum.EMAIL,
    "email marketing": ChannelEnum.EMAIL,
    "emailing": ChannelEnum.EMAIL,
    # Orgánico
    "organic": ChannelEnum.ORGANIC,
    "organico": ChannelEnum.ORGANIC,
    "orgánico": ChannelEnum.ORGANIC,
}


def normalize_channel(raw: str) -> ChannelEnum:
    """Convierte cualquier variante de canal al valor estándar."""
    key = raw.strip().lower()
    if key not in CHANNEL_MAP:
        raise ValueError(
            f"Canal desconocido: '{raw}'. "
            f"Valores aceptados: {[c.value for c in ChannelEnum]}"
        )
    return CHANNEL_MAP[key]


# ---------------------------------------------
# Schema: Venta individual (Fuente A)
# ---------------------------------------------
class SaleRecord(BaseModel):
    transaction_id: str
    customer_id: str
    amount: Decimal
    sale_date: date
    channel: str

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError(f"El monto debe ser positivo. Recibido: {v}")
        return v

    @field_validator("sale_date")
    @classmethod
    def date_cannot_be_future(cls, v: date) -> date:
        if v > datetime.now(timezone.utc).date():
            raise ValueError(f"La fecha no puede ser futura. Recibido: {v}")
        return v

    @field_validator("transaction_id", "customer_id")
    @classmethod
    def fields_cannot_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El campo no puede estar vacío")
        return v.strip()

    @field_validator("channel")
    @classmethod
    def normalize_channel_field(cls, v: str) -> str:
        return normalize_channel(v).value


# ---------------------------------------------
# Schema: Inversión publicitaria (Fuente B)
# ---------------------------------------------
class AdSpendRecord(BaseModel):
    spend_date: date
    channel: str
    cost: Decimal
    impressions: int
    clicks: int

    @field_validator("cost")
    @classmethod
    def cost_must_be_positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError(f"El costo no puede ser negativo. Recibido: {v}")
        return v

    @field_validator("spend_date")
    @classmethod
    def date_cannot_be_future(cls, v: date) -> date:
        if v > datetime.now(timezone.utc).date():
            raise ValueError(f"La fecha no puede ser futura. Recibido: {v}")
        return v

    @field_validator("impressions", "clicks")
    @classmethod
    def metrics_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"Las métricas no pueden ser negativas. Recibido: {v}")
        return v

    @field_validator("channel")
    @classmethod
    def normalize_channel_field(cls, v: str) -> str:
        return normalize_channel(v).value

    @model_validator(mode="after")
    def clicks_cannot_exceed_impressions(self) -> "AdSpendRecord":
        if self.clicks > self.impressions:
            raise ValueError(
                f"Los clics ({self.clicks}) no pueden superar "
                f"las impresiones ({self.impressions})"
            )
        return self


# ---------------------------------------------
# Resultado de validación — wrapper para el pipeline
# ---------------------------------------------
class ValidationResult(BaseModel):
    valid: list[SaleRecord | AdSpendRecord] = []
    rejected: list[dict] = []

    def add_valid(self, record: SaleRecord | AdSpendRecord) -> None:
        self.valid.append(record)

    def add_rejected(self, raw: dict, reason: str) -> None:
        self.rejected.append({"raw": raw, "reason": reason})

    @property
    def summary(self) -> str:
        return f"Válidos: {len(self.valid)} | Rechazados: {len(self.rejected)}"
