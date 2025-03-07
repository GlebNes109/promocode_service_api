from typing import Optional
from sqlalchemy import Column, Integer, Sequence
from sqlmodel import SQLModel, Field

# модель компаний
class CompanyDB(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    name: str
    email: str
    password_hash: str

# модель уникальных промокодов
class PromoUniqueDB(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    promo_id: str
    value: str
    is_activated: bool = Field(default=False)

# модель категорий промокодов
class PromoCategoryDB(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    promo_id: str
    name: str

# модель промокода
class PromocodeDB(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    company_id: str # а нужно ли foreign key?
    # active: bool
    used_count: int
    like_count: int
    mode: str
    description: str
    image_url: Optional[str]
    target_age_from: Optional[int]
    target_age_until: Optional[int]
    target_country: Optional[str]
    promo_common: Optional[str]
    max_count: int
    active_from: Optional[str]
    active_until: Optional[str]
    create_order: int = Field(sa_column=Column(Integer, Sequence("increment", start=1, increment=1), nullable=False))

class UserDB(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    name: str
    surname: str
    email: str
    avatar_url: Optional[str] = None
    other_age: int
    other_country: str
    password_hash: str

class UserLikeDB(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    promo_id: str
    user_id: str

class CommentDB(SQLModel, table=True):
    id: str =  Field(default=None, primary_key=True)
    text: str
    date: str
    author_id: str # user_id
    promo_id: str # айдишник промо на который коммент

class PromoCountryStatDB(SQLModel, table=True):
    id: str =  Field(default=None, primary_key=True)
    promo_id: str
    country: str

class UserActivatedPromo(SQLModel, table=True):
    id: str =  Field(default=None, primary_key=True)
    promo_id: str
    user_id: str
    activation_date: str