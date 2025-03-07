import uuid
from datetime import datetime

import pytz
from sqlalchemy import func, nullsfirst, nullslast, desc, text
from sqlalchemy.testing.plugin.plugin_base import logging
from sqlmodel import SQLModel, create_engine, Session, select
from env_variables import env_variables
from models.db_models import CompanyDB, PromocodeDB, PromoCategoryDB, PromoUniqueDB, UserLikeDB, CommentDB
from models.db_models import UserDB
from models.api_models import Promo, PromoPatch
from models.db_models import CommentDB
from models.db_models import UserActivatedPromo, PromoCountryStatDB

env_var = env_variables()


class DbController():
    def __init__(self):
        self.database_name = env_var.postgres_database
        self.username = env_var.postgres_username
        self.password = env_var.postgres_password
        self.host = env_var.postgres_host
        self.port = env_var.postgres_port
        DATABASE_URL = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database_name}"
        print(DATABASE_URL)
        self.engine = create_engine(DATABASE_URL)
        self.create_tables()

    def create_tables(self):
        try:
            # engine.url = f"postgresql://{username}:{password}@localhost/{database_name}"
            # SQLModel.metadata.drop_all(self.engine)
            SQLModel.metadata.create_all(self.engine)
            # print("Tables created successfully")
        except Exception as e:
            logging.error(e)

    def add_promocode(self, promo):
        promo_db = PromocodeDB(
            company_id=promo.company_id,
            active=True,
            used_count=0,
            like_count=0,
            mode=promo.mode,
            description=promo.description,
            # image_url=str(promo.image_url),
            promo_common=promo.promo_common,
            max_count=promo.max_count,
            active_from=promo.active_from,
            active_until=promo.active_until
        )
        if promo.target:
            promo_db.target_age_from = promo.target.age_from,
            promo_db.target_age_until = promo.target.age_until,
            promo_db.target_country = promo.target.country,

        if promo.image_url:
            promo_db.image_url = str(promo.image_url)

        promo_db.id = str(uuid.uuid4())
        uniqs_db, cats_db = [], []

        if promo.promo_unique:
            uniqs_db = [PromoUniqueDB(id=str(uuid.uuid4()), promo_id=promo_db.id, value=v) for v in promo.promo_unique]

        if promo.target and promo.target.categories:
            cats_db = [PromoCategoryDB(id=str(uuid.uuid4()), promo_id=promo_db.id, name=c) for c in promo.target.categories]

        with Session(self.engine) as session:
            session.add(promo_db)
            session.add_all(cats_db) # категории промо
            session.add_all(uniqs_db) # список промокодов

            session.commit()
            session.refresh(promo_db)

            return promo_db.id

    def add_company(self, company):
        with Session(self.engine) as session:
            company.id = str(uuid.uuid4())
            # token = self.create_jwt(company.id, company.name)
            session.add(company)
            session.commit()
            session.refresh(company)

    def get_promocodes_all(self):
        with Session(self.engine) as session:
            query = select(PromocodeDB)
            results = session.exec(query)
            res = results.all()
            return res

    def get_promocodes_cats_all(self):
        with Session(self.engine) as session:
            query = select(PromoCategoryDB)
            results = session.exec(query)
            res = results.all()
            return res

    def get_promocodes_cats(self, promo_id):
        with Session(self.engine) as session:
            query = select(PromoCategoryDB).where(PromoCategoryDB.promo_id == promo_id)
            results = session.exec(query)
            res = results.all()
            return res

    def get_promocodes_uniques(self, promo_id):
        with Session(self.engine) as session:
            query = select(PromoUniqueDB).where(PromoUniqueDB.promo_id == promo_id)
            results = session.exec(query)
            res = results.all()
            return res

    def get_promocodes_uniques_active(self, promo_id):
        with Session(self.engine) as session:
            query = select(PromoUniqueDB).where(PromoUniqueDB.promo_id == promo_id, PromoUniqueDB.is_activated == False)
            results = session.exec(query)
            res = results.all()
            return res

    def get_promocodes_unique_all(self):
        with Session(self.engine) as session:
            query = select(PromoUniqueDB)
            results = session.exec(query)
            res = results.all()
            return res

    def patch_promo_by_id(self, promo_patch: PromoPatch, id):
        with Session(self.engine) as session:
            query = select(PromocodeDB).where(PromocodeDB.id == id)
            promo_db = session.exec(query).first()
            # ==
            promo_db.description = promo_patch.description or promo_db.description
            # promo_db.image_url = str(promo_patch.image_url) or promo_db.image_url
            promo_db.max_count = promo_patch.max_count or promo_db.max_count
            promo_db.active_from = promo_patch.active_from or promo_db.active_from
            promo_db.active_until = promo_patch.active_until or promo_db.active_until

            if promo_patch.image_url:
                promo_db.image_url = str(promo_patch.image_url) or promo_db.image_url

            if promo_patch.target:
                promo_db.target_country = promo_patch.target.country or promo_db.target_country
                promo_db.target_age_from = promo_patch.target.age_from or promo_db.target_age_from
                promo_db.target_age_until = promo_patch.target.age_until or promo_db.target_age_until
                # promo_db.categories = promo_patch.target.categories or promo_db.categories
                session.query(PromoCategoryDB).where(PromoCategoryDB.promo_id == id).delete()

                if promo_patch.target.categories:
                    cats_db = [PromoCategoryDB(id=str(uuid.uuid4()), promo_id=promo_db.id, name=c) for c in
                               promo_patch.target.categories]
                    session.add_all(cats_db)  # категории промо
                # удалить добавить
            session.commit()
            session.refresh(promo_db)
            return promo_db

    def get_promocode_by_id(self, promo_id):
        with Session(self.engine) as session:
            query = select(PromocodeDB).where(PromocodeDB.id == promo_id)
            result = session.exec(query).first()
            return result

    def get_promocodes_with_pagination(self, limit, offset, company_id, sort_field=""):
        with Session(self.engine) as session:
            # query = None
            query = select(PromocodeDB).where(PromocodeDB.company_id == company_id).order_by(PromocodeDB.create_order.desc()).offset(offset).limit(limit)

            if sort_field == "active_from":
                query = select(PromocodeDB).where(PromocodeDB.company_id == company_id).order_by(nullslast(desc(PromocodeDB.active_from))).offset(offset).limit(limit)

            if sort_field == "active_until":
                query = select(PromocodeDB).where(PromocodeDB.company_id == company_id).order_by(nullsfirst(desc(PromocodeDB.active_from))).offset(offset).limit(limit)

            res = session.exec(query).all()
            total_query = select(func.count(PromocodeDB.id)).where(PromocodeDB.company_id == company_id)
            total = session.exec(total_query).one()

            return res, total

    def get_promocodes_with_pagination_country(self, limit, offset, company_id, country, sort_field=""):
        with Session(self.engine) as session:
            query = select(PromocodeDB).where(PromocodeDB.company_id == company_id).where(PromocodeDB.target_country.in_(country) | PromocodeDB.target_country.is_(None)).order_by(
                PromocodeDB.create_order.desc()).offset(offset).limit(limit)

            if sort_field == "active_from":
                query = select(PromocodeDB).where(PromocodeDB.company_id == company_id).where(PromocodeDB.target_country.in_(country) | PromocodeDB.target_country.is_(None)).order_by(
                    nullslast(desc(PromocodeDB.active_from))).offset(offset).limit(limit)

            if sort_field == "active_until":
                query = select(PromocodeDB).where(PromocodeDB.company_id == company_id).where(PromocodeDB.target_country.in_(country) | PromocodeDB.target_country.is_(None)).order_by(
                    nullsfirst(desc(PromocodeDB.active_from))).offset(offset).limit(limit)

            res = session.exec(query).all()

            total_query = select(func.count(PromocodeDB.id)).where(PromocodeDB.company_id == company_id).where(PromocodeDB.target_country.in_(country) | PromocodeDB.target_country.is_(None))
            total = session.exec(total_query).one()

            return res, total

    def get_companies(self):
        with Session(self.engine) as session:
            query = select(CompanyDB)
            results = session.exec(query)
            res = results.all()
            return res

    def get_company_by_id(self, company_id):
        with Session(self.engine) as session:
            query = select(CompanyDB).where(CompanyDB.id == company_id)
            results = session.exec(query).first()
            return results

    def company_exists_by_email(self, company):
        with Session(self.engine) as session:
            company_email = company.email
            query = select(CompanyDB).where(CompanyDB.email == company_email)
            result = session.exec(query).first()
            if result == None:
                return True
            else:
                return False

    def user_exists_by_email(self, user):
        with Session(self.engine) as session:
            query = select(UserDB).where(UserDB.email == user.email)
            result = session.exec(query).first()
            if result == None:
                return True
            else:
                return False

    def copmany_sign_in(self, email, password_hash):
        with Session(self.engine) as session:
            query = select(CompanyDB.id).where(CompanyDB.email == email, CompanyDB.password_hash == password_hash)
            res = session.exec(query).first() # получить айдишник компании. None если такой нет
            return res

    def user_sign_in(self, email, password_hash):
        with Session(self.engine) as session:
            query = select(UserDB.id).where(UserDB.email == email, UserDB.password_hash == password_hash)
            res = session.exec(query).first() # получить айдишник компании. None если такой нет
            return res

    def add_user(self, user_db):
        user_db.id = str(uuid.uuid4())
        with Session(self.engine) as session:
            session.add(user_db)
            session.commit()
            session.refresh(user_db)

    def patch_user(self, user_id, user_patch, password_hash=None):
        with Session(self.engine) as session:
            query = select(UserDB).where(UserDB.id == user_id)
            user_db = session.exec(query).first()

            user_db.name = user_patch.name or user_db.name
            user_db.surname = user_patch.surname or user_db.surname

            if user_patch.avatar_url:
                user_db.avatar_url = str(user_patch.avatar_url) or user_db.avatar_url

            if password_hash:
                user_db.password_hash = password_hash or user_db.password_hash

            session.commit()
            session.refresh(user_db)

    def get_users_all(self):
        with Session(self.engine) as session:
            query = select(UserDB)
            results = session.exec(query).all()
            return results

    def get_user_profile(self, user_id): # полчить по айдишнику юзверя
        with Session(self.engine) as session:
            query = select(UserDB).where(UserDB.id == user_id)
            results = session.exec(query).first()
            return results

    def add_user_like(self, user_id, promo_id):
        with Session(self.engine) as session:
            # если уже есть запись с такими айдишниками юзера и промо, ничего не делать.

            if not self.is_promo_liked_by_user(user_id, promo_id):
                user_like_db = UserLikeDB(user_id=user_id, promo_id=promo_id)
                user_like_db.id = str(uuid.uuid4())
                session.add(user_like_db)
                session.commit()
                session.refresh(user_like_db)

                # обновить счетчик лайков юзверя
                promo_db = session.exec(select(PromocodeDB).where(PromocodeDB.id == promo_id)).first()

                promo_db.like_count += 1

                session.commit()
                session.refresh(promo_db)

    def delete_user_like(self, user_id, promo_id):
        with Session(self.engine) as session:
            # если уже есть запись с такими айдишниками юзера и промо, ничего не делать.

            if self.is_promo_liked_by_user(user_id, promo_id):
                session.query(UserLikeDB).where(UserLikeDB.user_id == user_id,UserLikeDB.promo_id == promo_id ).delete()
                session.commit()

                # обновить счетчик лайков юзверя
                promo_db = session.exec(select(PromocodeDB).where(PromocodeDB.id == promo_id)).first()
                # if promo_db.like_count
                promo_db.like_count -= 1

                session.commit()
                session.refresh(promo_db)

    def delete_user_comment(self, user_id, comment_id, promo_id):
        with Session(self.engine) as session:
            session.query(CommentDB).where(CommentDB.id == comment_id).delete()
            session.commit()

    def is_promo_liked_by_user(self, user_id, promo_id):
        with Session(self.engine) as session:
            # если уже есть запись с такими айдишниками юзера и промо, ничего не делать.
            like_exist = select(func.count(UserLikeDB.id)).where(UserLikeDB.user_id == user_id, UserLikeDB.promo_id == promo_id)
            like_exist_cnt = session.exec(like_exist).one()
            if like_exist_cnt != 0:
                return True
            else:
                return False

    def get_that_crazy_promofeed_query_string(self, cat_flag, active_flag, counting_flag):
        return f"""
            with p as (
                select p.*,
                case 
                    when mode='COMMON' and used_count >= max_count then 0 
                    when to_date(active_from, 'YYYY-MM-DD') > current_date and active_from is not null then 0
                    when to_date(active_until, 'YYYY-MM-DD') < current_date and active_until is not null then 0
                    when mode='UNIQUE' and not exists(select 1 from promouniquedb pu where pu.promo_id = p.id) then 0
                    else 1 
                end as active
                From promocodedb p
                where (target_country is null or (target_country = :country))
                AND (target_age_from is null or (target_age_from <= :age))
                AND (target_age_until is null or (target_age_until >= :age))
                { "" if not cat_flag else "and id in ( select distinct promo_id from  promocategorydb where lower(name) = lower(:category))"}
                order by create_order desc
            )
            select { "count(*)" if counting_flag else " * " } from p
            { "where active = 1" if active_flag == "true" else "where active = 0" if active_flag == "false" else "" }
            { "" if counting_flag else "limit :limit offset :offset " } """

    def get_promocodes_for_user_with_pagination(self, limit, offset, user_db, category, active):
        with Session(self.engine) as session:

            query = text(self.get_that_crazy_promofeed_query_string(category, active, False))
            pars = {
                "country": user_db.other_country,
                "age": user_db.other_age,
                "category": category,
                "limit": limit,
                "offset": offset
            }

            res = session.exec(query, params=pars).mappings().all()

            total_query = text(self.get_that_crazy_promofeed_query_string(category, active, True))
            pars = {
                "country": user_db.other_country,
                "age": user_db.other_age,
                "category": category
            }
            total = session.exec(total_query, params=pars).one()[0]
            return res, total

    def add_user_comment(self, user_id, promo_id, text, date):
        with Session(self.engine) as session:
            user_comment_db = CommentDB(author_id=user_id, promo_id=promo_id, text=text, date=date)
            user_comment_db.id = str(uuid.uuid4())
            session.add(user_comment_db)
            session.commit()
            session.refresh(user_comment_db)
            return user_comment_db

    def get_promo_comments(self, limit, offset, promo_id):
        with Session(self.engine) as session:
            # query = None
            query = select(CommentDB, UserDB).join(UserDB, CommentDB.author_id == UserDB.id).where(CommentDB.promo_id == promo_id).order_by(CommentDB.date.desc()).offset(offset).limit(limit)
            res = session.exec(query).all()
            total_query = select(func.count(CommentDB.id)).where(CommentDB.promo_id == promo_id)
            total = session.exec(total_query).one()

            return res, total

    def get_comments_count(self, promo_id):
        with Session(self.engine) as session:
            # query = None
            total_query = select(func.count(CommentDB.id)).where(CommentDB.promo_id == promo_id)
            total = session.exec(total_query).one()

            return total

    def get_comment_by_id(self, comment_id, promo_id):
        with Session(self.engine) as session:
            query = select(CommentDB).where(CommentDB.id == comment_id, CommentDB.promo_id == promo_id)
            results = session.exec(query).first()

            return results

    def put_comment_by_id(self, comment_id, promo_id, text):
        with Session(self.engine) as session:
            query = select(CommentDB).where(CommentDB.id == comment_id, CommentDB.promo_id == promo_id)
            comment_db = session.exec(query).first()
            comment_db.text = text
            session.commit()
            session.refresh(comment_db)

            return comment_db

    def activate_common(self, promo_db):
        with Session(self.engine) as session:
            query = select(PromocodeDB).where(PromocodeDB.id == promo_db.id)
            promo_db_activate = session.exec(query).first()
            promo_db_activate.used_count += 1
            session.commit()
            session.refresh(promo_db_activate)

    def save_activate_country(self, promo_db, country):
        with Session(self.engine) as session:
            promo_stat = PromoCountryStatDB(promo_id=promo_db.id, country=country)
            promo_stat.id = str(uuid.uuid4())
            session.add(promo_stat)
            session.commit()

    def get_grouped_promo_countries(self, promo_id):
        with Session(self.engine) as session:
            statement = (
                select(PromoCountryStatDB.country, func.count(PromoCountryStatDB.promo_id).label("active_count"))
                .where(PromoCountryStatDB.promo_id == promo_id)
                .group_by(PromoCountryStatDB.country)
                .order_by(PromoCountryStatDB.country)
            )
            results = session.exec(statement).all()
            return results

    def activate_unique(self, promo_db):
        with Session(self.engine) as session:
            query = select(PromocodeDB).where(PromocodeDB.id == promo_db.id)
            promo_db_activate = session.exec(query).first()
            promo_db_activate.used_count += 1

            query = select(PromoUniqueDB).where(PromoUniqueDB.promo_id == promo_db.id, PromoUniqueDB.is_activated == False)
            promo_unique_activate = session.exec(query).first()
            promo_unique_activate.is_activated = True
            session.commit()
            session.refresh(promo_unique_activate)

            return promo_unique_activate.value

    def write_user_activate_promo(self, user_id, promo_id):
        user_activated_promo = UserActivatedPromo(
            promo_id=promo_id,
            user_id=user_id
        )
        user_activated_promo.id = str(uuid.uuid4())
        user_activated_promo.activation_date = datetime.now(pytz.timezone("Europe/Moscow")).isoformat()
        with Session(self.engine) as session:
            session.add(user_activated_promo)
            session.commit()
            session.refresh(user_activated_promo)

    def is_promo_activated_by_user(self, user_id, promo_id):
        with Session(self.engine) as session:
            query = select(UserActivatedPromo).where(UserActivatedPromo.user_id == user_id, UserActivatedPromo.promo_id == promo_id)
            user_activate_promo = session.exec(query).first()
            if user_activate_promo:
                return True
            else:
                return False

    def get_user_promo_history_with_pagination(self, limit, offset, user_id):
        with Session(self.engine) as session:
            # query = None
            query = select(UserActivatedPromo.promo_id).where(
                UserActivatedPromo.user_id == user_id).order_by(UserActivatedPromo.activation_date.desc()).offset(offset).limit(limit)
            res = session.exec(query).all()
            total_query = select(func.count(UserActivatedPromo.id)).where(UserActivatedPromo.user_id == user_id)
            total = session.exec(total_query).one()

            return res, total

