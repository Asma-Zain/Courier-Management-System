"""Pydantic request models. Whitelists come from config (same values as the CLI)."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import config

Status = Literal[tuple(config.VALID_STATUSES)]  # type: ignore[valid-type]
ShipmentType = Literal[tuple(config.SHIPMENT_TYPES)]  # type: ignore[valid-type]
PackageType = Literal[tuple(config.PACKAGE_TYPES)]  # type: ignore[valid-type]
PaymentMode = Literal[tuple(config.PAYMENT_MODES)]  # type: ignore[valid-type]
PaymentStatus = Literal[tuple(config.PAYMENT_STATUSES)]  # type: ignore[valid-type]


class Strict(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class LoginRequest(Strict):
    email: str = Field(min_length=3, max_length=120, examples=["divya@courier.com"])


class CustomerCreate(Strict):
    customerId: Optional[int] = Field(None, gt=0, description="Leave empty to auto-assign (max+1).",
                                      examples=[9001])
    firstName: str = Field(min_length=1, max_length=60, examples=["Sneha"])
    lastName: str = Field(min_length=1, max_length=60, examples=["Iyer"])
    email: str = Field(min_length=3, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                       examples=["sneha@example.com"])
    phone: str = Field(pattern=r"^\d{10}$", examples=["9876500005"])
    street: str = Field(min_length=1, max_length=120, examples=["5 Hill View"])
    city: str = Field(min_length=1, max_length=60, examples=["Chennai"])
    state: str = Field(min_length=1, max_length=60, examples=["Tamil Nadu"])
    pincode: str = Field(pattern=r"^\d{6}$", examples=["600020"])


class CustomerUpdate(Strict):
    phone: Optional[str] = Field(None, pattern=r"^\d{10}$", examples=["9876500099"])
    street: Optional[str] = Field(None, min_length=1, max_length=120)
    city: Optional[str] = Field(None, min_length=1, max_length=60)
    state: Optional[str] = Field(None, min_length=1, max_length=60)
    pincode: Optional[str] = Field(None, pattern=r"^\d{6}$")


class PackageIn(Strict):
    description: str = Field(min_length=1, max_length=120, examples=["Gift box"])
    dimensions: str = Field(min_length=1, max_length=40, examples=["30x30x15 cm"])
    packageType: PackageType = Field(examples=["Box"])
    weightKg: float = Field(gt=0, le=1000, examples=[2.0])


class BookingPayment(Strict):
    mode: PaymentMode = Field(examples=["UPI"])
    status: PaymentStatus = Field("PAID", examples=["PAID"])


class ShipmentCreate(Strict):
    sender: Optional[int] = Field(None, gt=0, description="Customer id. Customers always send as themselves.",
                                  examples=[1])
    receiver: Optional[int] = Field(None, gt=0, examples=[2])
    receiverEmail: Optional[str] = Field(None, max_length=120, examples=["priya@example.com"])
    payment: Optional[BookingPayment] = Field(None, description="Staff only: record the payment at booking.")
    branchId: int = Field(gt=0, description="Booking branch id.", examples=[1])
    shipmentType: ShipmentType = Field(examples=["STANDARD"])
    packages: list[PackageIn] = Field(min_length=1, max_length=50)
    totalAmount: Optional[float] = Field(None, gt=0, description="Leave empty to use the demo rate card.")


class EventCreate(Strict):
    status: Status = Field(examples=["IN_TRANSIT"])
    note: Optional[str] = Field(None, max_length=200, description="Optional note shown in the journey.")
    branch: str = Field(min_length=1, max_length=80, description="Branch or hub name.",
                        examples=["Hyderabad Hub"])

    @field_validator("status", mode="before")
    @classmethod
    def _upper(cls, v):
        return v.strip().upper() if isinstance(v, str) else v


class PaymentCreate(Strict):
    amount: float = Field(gt=0, examples=[150.0])
    mode: PaymentMode = Field(examples=["UPI"])
    status: PaymentStatus = Field("PAID", examples=["PAID"])
