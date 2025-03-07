import hashlib
import time
from fastapi import Request, Response, Query
from datetime import datetime

import pytz
import jwt
from fastapi import Depends
from fastapi import FastAPI
import uvicorn
from fastapi.exceptions import RequestValidationError, HTTPException
from pycountry import countries
# from requests.packages import target
from starlette.responses import JSONResponse

from dbController import DbController
from env_variables import env_variables
from models.api_models import Company, Promo, UserRegister, Target, PromoPatch, SignIn, User, Text
from models.db_models import CompanyDB, UserDB
from RedisController import RedisController
from models.api_models import PromoReadOnly
from models.api_models import PromoPatch
from models.api_models import UserTargetSettings
from models.api_models import UserPatch
from models.api_models import PromoForUser
from models.api_models import Comment, CommentAuthor
from AntifraudController import AntifraudController
from models.api_models import PromoStat, PromoCountryStat

# env_variables.value
env_var= env_variables()

SECRET_KEY = env_var.secret
ALGORITHM = "HS256"
app = FastAPI()
dbcon = DbController()
redis_con = RedisController()

def convert_userdb_to_apimodel(user_db):
    other_db = UserTargetSettings(
        age=user_db.other_age,
        country=user_db.other_country
    )

    user = User(
        name=user_db.name,
        surname=user_db.surname,
        email=user_db.email,
        # avatar_url=user_db.avatar_url,
        other=other_db.model_dump()
    )

    if user_db.avatar_url:
        user.avatar_url = user_db.avatar_url

    return user

def convert_promodb_to_apimodel(promo_db):
    cats = dbcon.get_promocodes_cats(promo_db.id)
    if cats:
        cats = [i.name for i in cats]

    promo_uniques = dbcon.get_promocodes_uniques(promo_db.id)
    if promo_uniques:
        promo_uniques = [i.value for i in promo_uniques]

    company_id = promo_db.company_id
    company = dbcon.get_company_by_id(company_id)

    promo_target = Target(
        age_from=promo_db.target_age_from,
        age_until=promo_db.target_age_until,
        country=promo_db.target_country,
        categories=cats
    )
    promo = PromoReadOnly(
        description=promo_db.description,
        # image_url=str(promo_db.image_url),
        target=promo_target.model_dump(),
        max_count=promo_db.max_count,
        active_from=promo_db.active_from,
        active_until=promo_db.active_until,
        mode=promo_db.mode,
        promo_common=promo_db.promo_common,
        promo_unique=promo_uniques,
        promo_id=promo_db.id,
        company_id=company_id,
        company_name=company.name,
        like_count=promo_db.like_count,
        used_count=promo_db.used_count,
        active=is_promo_active(promo_db)
    )

    if promo.target == None:
        promo.target = {}

    if promo_db.image_url:
        promo.image_url = promo_db.image_url

    return promo

def is_promo_active(promo_db):
    valid_date = True
    valid_activations = True
    current_date_str = (datetime.now().strftime("%Y-%m-%d"))
    start_date_str = promo_db.active_from
    end_date_str = promo_db.active_until
    current_date = datetime.strptime(current_date_str, '%Y-%m-%d').date()

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if start_date > current_date:
            valid_date = False

    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        if end_date < current_date:
            valid_date = False

    promo_uniques = dbcon.get_promocodes_uniques_active(promo_db.id)

    if promo_db.mode == "COMMON" and promo_db.used_count >= promo_db.max_count:
        valid_activations = False

    if promo_db.mode == "UNIQUE" and not promo_uniques:
        valid_activations = False

    return valid_date and valid_activations

def is_valid_date(start_date_str, end_date_str, current_date_str):
    valid_date = True
    current_date = datetime.strptime(current_date_str, '%Y-%m-%d').date()

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if start_date > current_date:
            valid_date = False

    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        if end_date < current_date:
            valid_date = False

    return valid_date

def get_token(request: Request):
    headers = request.headers
    a = str(headers.get("Authorization"))
    return a[7:]

def create_hash(password):
    sha256hash = hashlib.sha256()
    sha256hash.update(password.encode('utf-8'))
    return sha256hash.hexdigest()

def create_jwt_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def calculate_token_TTL():
    TTL = time.time() + 14400 # 4 часа
    return TTL

def make_http_error(code, text):
    return JSONResponse(
        status_code=code,
        content={
            "status": "error",
            "message": text
        })

def get_company(token: str = Depends(get_token)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        company_id = payload.get("sub")

        if not dbcon.get_company_by_id(company_id):
            raise jwt.PyJWTError

        if not redis_con.validate_key(str(company_id), str(token)):
            raise jwt.PyJWTError

        return company_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="пользователь не авторизован")

def get_user(token: str = Depends(get_token)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if not dbcon.get_user_profile(user_id):
            raise jwt.PyJWTError

        if not redis_con.validate_key(str(user_id), str(token)):
            raise jwt.PyJWTError

        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="пользователь не авторизован")
        # raise make_http_error(401, "пользователь не авторизован")

@app.exception_handler(RequestValidationError)
async def raise_validation_error(request: Request, exc: RequestValidationError):
    return make_http_error(400, "ошибка в данных запроса")

@app.get("/api/ping")
def send():
    return {"status": "PROD"}

# регистрация новой компании
@app.post("/api/business/auth/sign-up")
def sign_up(company: Company):
    company_db = CompanyDB(name=company.name, email=company.email, password_hash=create_hash(company.password))

    if dbcon.company_exists_by_email(company_db):
        dbcon.add_company(company_db)
        token = create_jwt_token({"sub": company_db.id, "exp": calculate_token_TTL()})
        # print(create_jwt_token({"sub": company_db.id, "exp": calculate_token_TTL()}))
        # print(token)
        response = {"token": token, "company_id": company_db.id}
        # print(company_db.id)
        redis_con.add_key_to_db(str(company_db.id), token)
        return response
    else:
        return make_http_error(409, "Такой email уже зарегистрирован.")
        # raise HTTPException(status_code=409, detail="Такой email уже зарегистрирован.")
        # return {"status": "error", "message": "Такой email уже зарегистрирован."}

# аутентификация существующей компании
@app.post("/api/business/auth/sign-in")
def sign_in(company_sign_in: SignIn):
    company_id = dbcon.copmany_sign_in(company_sign_in.email, create_hash(company_sign_in.password))
    if company_id:
        token = create_jwt_token({"sub": company_id, "exp": calculate_token_TTL()})
        response = {"token": token, "company_id": company_id}
        # print(company_id)
        redis_con.add_key_to_db(str(company_id), token)
        return response
    else:
        return make_http_error(401, "Неверный email или пароль.")
    # redis_con.add_key_to_db()
    # TODO: аннулировать все предыдущие токены -_- не знаю как. Хранить их В РЕДИСЕ!

@app.post("/api/business/promo")
def create(promo: Promo, company_id: str = Depends(get_company)):
    promo.company_id = company_id
    promo_id = dbcon.add_promocode(promo)

    return JSONResponse(status_code=201,content={"id": promo_id})

@app.post("/api/user/auth/sign-up")
def sign_up_user(user: UserRegister):

    user_db = UserDB(
        name=user.name,
        surname=user.surname,
        email=user.email,
        # avatar_url=str(user.avatar_url),
        other_age=user.other.age,
        other_country=user.other.country,
        password_hash=create_hash(user.password)
    )

    if user.avatar_url:
        user_db.avatar_url = str(user.avatar_url)

    if dbcon.user_exists_by_email(user):
        # user.password = create_hash(user.password)
        dbcon.add_user(user_db)
        token = create_jwt_token({"sub": user_db.id, "exp": calculate_token_TTL()})
        response = {"token": token, "user_id": user_db.id}
        redis_con.add_key_to_db(str(user_db.id), token)
        return response
    else:
        return make_http_error(409, "Такой email уже зарегистрирован.")

@app.post("/api/user/auth/sign-in")
def sign_up_user(user_sign_in: SignIn):
    user_id = dbcon.user_sign_in(user_sign_in.email, create_hash(user_sign_in.password))
    if user_id:
        token = create_jwt_token({"sub": user_id, "exp": calculate_token_TTL()})
        response = {"token": token, "company_id": user_id}
        redis_con.add_key_to_db(str(user_id), token)
        return response
    else:
        return make_http_error(401, "Неверный email или пароль.")

@app.get("/api/business/promo/{id}")
def get_promo(id: str, company_id: str = Depends(get_company)):
    promo_db = dbcon.get_promocode_by_id(id)

    if not promo_db:
        return make_http_error(404, "промокод не найден")

    if promo_db.company_id != company_id:
        return make_http_error(403, "промокод не принадлежит этой компании")

    promo = convert_promodb_to_apimodel(promo_db)

    return promo

@app.get("/api/business/promo")
def get_list_promo(response: Response, limit: int = 10, offset: int = 0, sort_by: str = None, country: list[str] = Query(None), company_id: str = Depends(get_company)):
    if country:
        for i in range(len(country)):
            if ',' in country[i]:
                st = country.pop(i).split(',')
                country += st
    if country:
        promocodes, count = dbcon.get_promocodes_with_pagination_country(limit, offset, company_id, country, sort_by)
    else:
        promocodes, count = dbcon.get_promocodes_with_pagination(limit, offset, company_id, sort_by)

    promocodes_api = []

    for promo_db in promocodes:
        promocodes_api.append(convert_promodb_to_apimodel(promo_db))

    response.headers["X-Total-Count"] = str(count)

    return promocodes_api

@app.patch("/api/business/promo/{id}")
def patch_promocode_by_id(id: str, promo_patch: PromoPatch, company_id: str = Depends(get_company)):
    promo_db = dbcon.get_promocode_by_id(id)

    if not promo_db:
        return make_http_error(404, "промокод не найден")

    if promo_db.company_id != company_id:
        return make_http_error(403, "промокод не принадлежит этой компании")

    if promo_db.mode == "UNIQUE" and promo_patch.max_count and promo_patch.max_count != 1:
        return make_http_error(400, "Ошибка в данных запроса")

    promo_db = dbcon.patch_promo_by_id(promo_patch, id)

    cats = dbcon.get_promocodes_cats(promo_db.id)
    if cats:
        cats = [i.name for i in cats]

    promo_uniques = dbcon.get_promocodes_uniques(promo_db.id)
    if promo_uniques:
        promo_uniques = [i.value for i in promo_uniques]

    company = dbcon.get_company_by_id(company_id)

    return convert_promodb_to_apimodel(promo_db)

@app.get("/api/user/profile")
def get_user_profile(user_id: str = Depends(get_user)):
    user_db = dbcon.get_user_profile(user_id)
    user = convert_userdb_to_apimodel(user_db)
    return user

@app.patch("/api/user/profile")
def patch_user_profile(user_patch: UserPatch, user_id: str = Depends(get_user)):
    password_hash = None
    if user_patch.password:
        password_hash = create_hash(user_patch.password)

    dbcon.patch_user(user_id, user_patch, password_hash)
    get_user_profile(user_id)
    user_db = dbcon.get_user_profile(user_id)
    user = convert_userdb_to_apimodel(user_db)
    return user

@app.get("/api/user/feed")
def get_user_feed(response: Response, limit: int = 10, offset: int = 0, category: str = None, active: str = None, user_id: str = Depends(get_user)):
    user_db = dbcon.get_user_profile(user_id)

    promo_list, total = dbcon.get_promocodes_for_user_with_pagination(limit, offset, user_db, category, active)
    promo_list_for_api = [convert_promodb_to_promouser_apimodel(promo_db, user_id) for promo_db in promo_list]

    response.headers["X-Total-Count"] = str(total)
    return promo_list_for_api

@app.get("/api/user/promo/history")
def get_history(response: Response, limit: int = 10, offset: int = 0, user_id: str = Depends(get_user)):
    promo_id_list, total = dbcon.get_user_promo_history_with_pagination(limit, offset, user_id)
    promo_list_api = []
    for promo_id in promo_id_list:
        promo_db = dbcon.get_promocode_by_id(promo_id)
        company_db = dbcon.get_company_by_id(promo_db.company_id)
        promo_api_user = PromoForUser(
            promo_id=promo_id,
            company_id=promo_db.company_id,
            company_name=company_db.name,
            description=promo_db.description,
            active=is_promo_active(promo_db),
            is_activated_by_user = dbcon.is_promo_activated_by_user(user_id, promo_db.id),  # TODO: ещк одна таблица в бд промокод / активация юзера ключ значение
            like_count = promo_db.like_count,
            is_liked_by_user = dbcon.is_promo_liked_by_user(user_id, promo_db.id),
            comment_count = dbcon.get_comments_count(promo_db.id)
        )
        if promo_db.image_url:
            promo_api_user.image_url = str(promo_db.image_url)

        promo_list_api.append(promo_api_user)

    response.headers["X-Total-Count"] = str(total)

    return promo_list_api

@app.get("/api/user/promo/{id}")
def get_user_promo(id: str, user_id: str = Depends(get_user)):
    promo_db = dbcon.get_promocode_by_id(id)

    if not promo_db:
        return make_http_error(404, "промокод не найден")

    promo_api_user = convert_promodb_to_promouser_apimodel(promo_db, user_id)

    return promo_api_user

def convert_promodb_to_promouser_apimodel(promo_db, user_id):

    company_db = dbcon.get_company_by_id(promo_db.company_id)

    promo_api_user = PromoForUser(
        promo_id=promo_db.id,
        company_id=company_db.id,
        company_name=company_db.name,
        description=promo_db.description,
        # image_url=
        active=is_promo_active(promo_db),
        is_activated_by_user=dbcon.is_promo_activated_by_user(user_id, promo_db.id),  # TODO: ещк одна таблица в бд промокод / активация юзера ключ значение
        like_count=promo_db.like_count,
        is_liked_by_user=dbcon.is_promo_liked_by_user(user_id, promo_db.id),
        comment_count=dbcon.get_comments_count(promo_db.id)
    )
    if promo_db.image_url:
        promo_api_user.image_url = str(promo_db.image_url)

    return promo_api_user

@app.post("/api/user/promo/{id}/like")
def add_user_like(id: str, user_id: str = Depends(get_user)):
    promo_db = dbcon.get_promocode_by_id(id)
    if not promo_db:
        return make_http_error(404, "промокод не найден")

    dbcon.add_user_like(user_id, id)

    return JSONResponse(status_code=200,content={"status": "ok"})

@app.delete("/api/user/promo/{id}/like")
def delete_user_like(id: str, user_id: str = Depends(get_user)):
    promo_db = dbcon.get_promocode_by_id(id)
    if not promo_db:
        return make_http_error(404, "промокод не найден")

    dbcon.delete_user_like(user_id, id)

    return JSONResponse(status_code=200,content={"status": "ok"})

@app.post("/api/user/promo/{id}/comments")
def add_user_comment(text: Text, id: str, user_id: str = Depends(get_user)):
    promo_db = dbcon.get_promocode_by_id(id)
    if not promo_db:
        return make_http_error(404, "промокод не найден")

    text = text.text

    date = datetime.now(pytz.timezone("Europe/Moscow")).isoformat()
    comment_db = dbcon.add_user_comment(user_id, id, text, date)
    user_db = dbcon.get_user_profile(user_id)

    author = CommentAuthor(
        name=user_db.name,
        surname=user_db.surname,
        avatar_url=user_db.avatar_url
    )

    comment_api = Comment(
        id=comment_db.id,
        text=comment_db.text,
        date=comment_db.date,
        author=author
    )
    return JSONResponse(status_code=201,content=comment_api.model_dump())

def convert_commentdb_to_commentapi(comment_db, user_db):
    author_api = CommentAuthor(
        name=user_db.name,
        surname=user_db.surname,
        avatar_url=user_db.avatar_url
    )

    comment_api = Comment(
        id=comment_db.id,
        text=comment_db.text,
        date=comment_db.date,
        author=author_api
    )

    return comment_api

@app.get("/api/user/promo/{id}/comments")
def get_promo_comments(response: Response, id: str, limit: int = 10, offset: int = 0, user_id: str = Depends(get_user)):
    promo_db = dbcon.get_promocode_by_id(id)
    if not promo_db:
        return make_http_error(404, "промокод не найден")

    comments, total = dbcon.get_promo_comments(limit, offset, id)

    comments_for_api = [convert_commentdb_to_commentapi(comment_db, user_db) for comment_db, user_db in comments]

    response.headers["X-Total-Count"] = str(total)
    return comments_for_api

@app.get("/api/user/promo/{id}/comments/{comment_id}")
def get_promo_comment_by_companyid(id: str, comment_id: str, user_id: str = Depends(get_user)):
    promo_db = dbcon.get_promocode_by_id(id)

    if not promo_db:
        return make_http_error(404, "промокод не найден")

    comment_db = dbcon.get_comment_by_id(comment_id, promo_db.id)

    if not comment_db:
        return make_http_error(404, "комментарий не найден")

    user_db = dbcon.get_user_profile(user_id)
    return convert_commentdb_to_commentapi(comment_db, user_db)

@app.put("/api/user/promo/{id}/comments/{comment_id}")
def put_promo_comment_by_companyid(text: Text, id: str, comment_id: str, user_id: str = Depends(get_user)):
    promo_db = dbcon.get_promocode_by_id(id)
    if not promo_db:
        return make_http_error(404, "промокод не найден")

    comment_db = dbcon.get_comment_by_id(comment_id, promo_db.id)
    if not comment_db:
        return make_http_error(404, "комментарий не найден")

    if comment_db.author_id != user_id:
        return make_http_error(403, "комментарий не принадлежит пользователю")

    comment_db = dbcon.put_comment_by_id(comment_id, promo_db.id, text.text)

    user_db = dbcon.get_user_profile(user_id)
    return convert_commentdb_to_commentapi(comment_db, user_db)

@app.delete("/api/user/promo/{id}/comments/{comment_id}")
def delete_user_comment(id: str, comment_id: str, user_id: str = Depends(get_user)):
    promo_db = dbcon.get_promocode_by_id(id)
    if not promo_db:
        return make_http_error(404, "промокод не найден")

    comment_db = dbcon.get_comment_by_id(comment_id, promo_db.id)
    if not comment_db:
        return make_http_error(404, "комментарий не найден")

    if comment_db.author_id != user_id:
        return make_http_error(403, "комментарий не принадлежит пользователю")

    dbcon.delete_user_comment(user_id, comment_id, promo_db.id)

    return JSONResponse(status_code=200,content={"status": "ok"})

@app.post("/api/user/promo/{id}/activate")
def activate_promo(id: str, user_id: str = Depends(get_user)):
    promo_db = dbcon.get_promocode_by_id(id)

    if not promo_db:
        return make_http_error(404, "промокод не найден")

    antifraud_res = redis_con.get_user_antifraud_result(user_id)

    if not antifraud_res:
        afcon = AntifraudController()
        user_db = dbcon.get_user_profile(user_id)
        af_json = afcon.check_user(user_db.email, id)
        cache_until = af_json["cache_until"]
        antifraud_res = af_json["ok"]

        redis_con.save_user_antifraud_result(user_id, antifraud_res, cache_until)

    if str(antifraud_res) == 'False':
        return make_http_error(403, "вы не можете использовать этот промокод (антифрод)")

    if not is_promo_active(promo_db):
        return make_http_error(403, "вы не можете использовать этот промокод (не активен)")

    user_db = dbcon.get_user_profile(user_id)
    if promo_db.target_age_from and promo_db.target_age_from > user_db.other_age:
        return make_http_error(403, "вы не можете использовать этот промокод (таргетинг фром)")

    if promo_db.target_age_until and promo_db.target_age_until < user_db.other_age:
        return make_http_error(403, "вы не можете использовать этот промокод (таргетинг антил)")

    if promo_db.target_country and promo_db.target_country.lower() != user_db.other_country.lower():
        return make_http_error(403, "вы не можете использовать этот промокод (таргетинг страна)")

    # =============

    if promo_db.mode == "COMMON":
        dbcon.activate_common(promo_db)
        dbcon.save_activate_country(promo_db, user_db.other_country)
        dbcon.write_user_activate_promo(user_db.id, promo_db.id)
        return JSONResponse(status_code=200, content={"promo": promo_db.promo_common})

    if promo_db.mode == "UNIQUE":
        unique = dbcon.activate_unique(promo_db)
        dbcon.save_activate_country(promo_db, user_db.other_country)
        dbcon.write_user_activate_promo(user_db.id, promo_db.id)
        return JSONResponse(status_code=200, content={"promo": unique})

@app.get("/api/business/promo/{id}/stat")
def activate_promo(id: str, company_id: str = Depends(get_company)):
    if not id:
        return make_http_error(400, "ошибка в данных запроса")

    promo_db = dbcon.get_promocode_by_id(id)

    if not promo_db:
        return make_http_error(404, "промокод не найден")

    if promo_db.company_id != company_id:
        return make_http_error(403, "промокод не принадлежит компании")

    promo_stat = PromoStat(activations_count=promo_db.used_count)

    grouped_promo_countries = dbcon.get_grouped_promo_countries(promo_db.id)
    if grouped_promo_countries != None:
        promo_stat.countries =  [PromoCountryStat(country=country, activations_count=active_count) for country, active_count in grouped_promo_countries]

    return promo_stat



if __name__ == "__main__":
    server_address = env_var.server_address
    host, port = server_address.split(":")
    uvicorn.run(app, host=host, port=int(port))
