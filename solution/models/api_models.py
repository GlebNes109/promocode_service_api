from typing import Optional, Any, Self
from pydantic import EmailStr, BaseModel, field_validator, model_validator, AnyUrl
from sqlmodel import Field
import re
import pycountry
from datetime import datetime


# модель компании для запросов HTTP
class Company(BaseModel):
    name: Optional[str] = Field(default=None, min_length=5, max_length=50)
    email: EmailStr = Field(..., min_length=8, max_length=120)
    password: str = Field(..., min_length=8, max_length=60)
    @field_validator("password", mode="after")
    def validate_password(cls, password: str):
        pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        if re.fullmatch(pattern, password):
            return password
        else:
            raise ValueError

class Target(BaseModel):
    age_from: Optional[int] = Field(default=None, ge=0, le=100)
    age_until: Optional[int] = Field(default=None, ge=0, le=100)
    country: Optional[str] = None
    categories: Optional[list[str]] = None
    @model_validator(mode="after")
    def validate(self):
        if self.age_from and self.age_until and self.age_from > self.age_until:
            raise ValueError
        if self.categories and len([i for i in self.categories if len(i) < 2 or len(i) > 20]) > 0:
            raise ValueError
        if self.country and self.country.upper() not in [country.alpha_2 for country in pycountry.countries]:
            raise ValueError
        return self

class Promo(BaseModel):
   # promo_id: Optional[str] = None
    like_count: Optional[int] = None
    used_count: Optional[int] = None
    active: Optional[bool] = None
    company_id: Optional[str] = None
    description: str = Field(min_length=10, max_length=300)
    image_url: Optional[AnyUrl] = Field(default=None, max_length=350)
    target: Target | None
    max_count: int
    active_from: Optional[str] = None
    active_until: Optional[str] = None
    mode: str
    promo_common: Optional[str] = Field(default=None, min_length=5, max_length=30)
    promo_unique: Optional[list[str]] = None

    @model_validator(mode="after")
    def validate(self):
        if self.mode == "COMMON" and not self.promo_common:
            raise ValueError
        if self.mode == "UNIQUE" and not self.promo_unique:
            raise ValueError
        if self.mode != "COMMON" and self.mode != "UNIQUE":
            raise ValueError
        if self.mode == "COMMON" and self.promo_unique:
            raise ValueError
        if self.mode == "UNIQUE" and self.promo_common:
            raise ValueError
        if self.mode == "COMMON" and (self.max_count < 0 or self.max_count > 100000000):
            raise ValueError
        if self.mode == "UNIQUE" and not self.max_count == 1:
            raise ValueError
        # валидации на длину в категориях - от 2 до 20
        # валидация на длину строк в промо юник - от 3 до 30
        # валидация на кол-во списка промокодов
        if self.mode == "UNIQUE" and (len(self.promo_unique) < 1 or len(self.promo_unique) > 5000):
            raise ValueError
        if self.mode == "UNIQUE":
            if len([i for i in self.promo_unique if len(i) < 3 or len(i) > 30]) > 0:
                raise ValueError
        if self.target and self.target.categories and len([i for i in self.target.categories if len(i) < 2 or len(i) > 20]) > 0:
            raise ValueError
        if self.target and self.target.country and self.target.country.upper() not in [country.alpha_2 for country in pycountry.countries]:
            raise ValueError
        return self

class PromoReadOnly(BaseModel):
    description: str = Field(default=None, min_length=10, max_length=300)
    image_url: Optional[AnyUrl] = Field(default=None, max_length=350)
    target: Target
    max_count: int
    active_from: Optional[str] = None
    active_until: Optional[str] = None
    mode: str
    promo_common: Optional[str] = Field(default=None, min_length=5, max_length=30)
    promo_unique: Optional[list[str]] = None
    promo_id: str
    company_id: str
    company_name: str
    like_count: int
    used_count: int
    active: bool

class UserTargetSettings(BaseModel):
    age: int = Field(..., ge=0, le=100)
    country: str
    @model_validator(mode="after")
    def validate(self):
        if self.country.upper() not in [country.alpha_2 for country in pycountry.countries]:
            raise ValueError
        return self

class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    surname: str = Field(..., min_length=1, max_length=120)
    email: EmailStr = Field(..., min_length=8, max_length=120)
    avatar_url: Optional[AnyUrl] = Field(default=None, max_length=350)
    other: UserTargetSettings
    password: str = Field(..., min_length=8, max_length=60)
    @model_validator(mode="after")
    def validate(self):
        if self.other.country.upper() not in [country.alpha_2 for country in pycountry.countries]:
            raise ValueError

        pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"

        if not re.fullmatch(pattern, self.password):
            raise ValueError
        return self

class PromoForUser(BaseModel):
    promo_id: str #uuid
    company_id: str
    company_name: str = Field(min_length=5, max_length=50)
    description: str = Field(min_length=10, max_length=300)
    image_url: Optional[str] = Field(default=None, max_length=350)
    active: bool
    is_activated_by_user: bool
    like_count:  int = Field(ge=0)
    is_liked_by_user: bool
    comment_count: int = Field(ge=0)

class User(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    surname: str = Field(..., min_length=1, max_length=120)
    email: EmailStr = Field(..., min_length=8, max_length=120)
    avatar_url: Optional[AnyUrl] = Field(default=None, max_length=350)
    other: UserTargetSettings
    # password: str = Field(..., min_length=8, max_length=60)

    @model_validator(mode="after")
    def validate(self):
        if self.other.country.upper() not in [country.alpha_2 for country in pycountry.countries]:
            raise ValueError
        # pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        return self

class SignIn(BaseModel):
    email: EmailStr = Field(..., min_length=8, max_length=120)
    password: str = Field(..., min_length=8, max_length=60)
    @field_validator("password", mode="after")
    def validate_password(cls, password: str):
        pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        if re.fullmatch(pattern, password):
            return password
        else:
            raise ValueError

class PromoPatch(BaseModel):
    description: Optional[str] = Field(default=None, min_length=10, max_length=300)
    image_url: Optional[AnyUrl] = Field(default=None, max_length=350)
    target: Optional[Target] = None
    max_count: Optional[int] = None
    active_from: Optional[str] = None
    active_until: Optional[str] = None

    @model_validator(mode="after")
    def validate(self):
        dateregexp = r'^\d{4}-\d{2}-\d{2}$'
        if self.active_from and not re.match(dateregexp, self.active_from):
            raise ValueError
        if self.active_until and not re.match(dateregexp, self.active_until):
            raise ValueError
        return self

class UserPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    surname: Optional[str] = Field(default=None, min_length=1, max_length=120)
    # email: EmailStr = Field(..., min_length=8, max_length=120)
    avatar_url: Optional[AnyUrl] = Field(default=None, max_length=350)
    password: Optional[str] = Field(default=None, min_length=8, max_length=60)

    @model_validator(mode="after")
    def validate(self):
        pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"

        if self.password and not re.fullmatch(pattern, self.password):
            raise ValueError
        return self

class CommentAuthor(BaseModel):
    name: str = Field(None, min_length=1, max_length=100)
    surname: str = Field(None, min_length=1, max_length=120)
    avatar_url: Optional[str] = Field(default=None, max_length=350) #url не может быть не url потому что берем валидированный уже из базы

class Comment(BaseModel):
    id: Optional[str] = None
    text: Optional[str] = Field(default=None, min_length=10, max_length=100)
    date: Optional[str] = None
    author: CommentAuthor

    @field_validator('date')
    def validate_rfc3339_format(cls, date: str):
        try:
            datetime.fromisoformat(date)
        except:
            raise ValueError
        return date

class Text(BaseModel):
    text: str = Field(default=None, min_length=10, max_length=1000)

class PromoCountryStat(BaseModel):
    country: str
    activations_count: int = Field(ge=1)

class PromoStat(BaseModel):
    activations_count: int = Field(ge=0)
    countries: Optional[list[PromoCountryStat]] = None
