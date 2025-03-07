from sqlalchemy.testing import resolve_lambda

from dbController import DbController

db = DbController()

print("\n** Companies **")
res = db.get_companies()
for c in res:
    print(c)

print("\n** Promocodes **")
res = db.get_promocodes_all()
for p in res:
    print(p)

print("\n** Promo categories **")
res = db.get_promocodes_cats_all()
for p in res:
    print(p)

print("\n** Promo Uniques **")
res = db.get_promocodes_unique_all()
for p in res:
    print(p)

print("\n** Users **")
res = db.get_users_all()
for p in res:
    print(p)

print("***")
res = db.get_promocodes_for_user_with_category(10, 0, "4650d6e4-9fa5-4ca1-8217-999c26d9c0a5", "")

for p in res:
    print(p)