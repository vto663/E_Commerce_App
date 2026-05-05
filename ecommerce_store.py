import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "ecommerce_catalog")

def get_client():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    return client


class ECommerceStore:
    
    def __init__(self):
        self.client = get_client()
        self.database = self.client[DB_NAME]
        self.products = self.database["products"]
        self.variants = self.database["variants"]
        self.categories = self.database["categories"]
        print(f"Свързах се с базата: {DB_NAME}")
        print(f"   - Продукти: {self.products.count_documents({})} бр.")
        print(f"   - Варианти: {self.variants.count_documents({})} бр.")
        print(f"   - Категории: {self.categories.count_documents({})} бр.")
    
    def close_connection(self):
        self.client.close()
        print("Връзката затворена")
    

    def add_product(self, title: str, brand: str, category_id: int, price: float, 
                    rating: float = 3.0, in_stock: bool = True) -> str:

        last_product = self.products.find_one(sort=[("_id", -1)])
        next_id = (last_product["_id"] + 1) if last_product else 1
        
        doc = {
            "_id": next_id,
            "title": title,
            "slug": title.lower().replace(" ", "-"),
            "brand": brand,
            "category_id": category_id,
            "price": price,
            "discount_price": None,
            "rating": rating,
            "in_stock": in_stock,
            "attributes": {},
            "tags": [],
            "created_at": None,
            "updated_at": None,
            "search_keywords": f"{brand} {title}"
        }
        try:
            result = self.products.insert_one(doc)
            print(f"Добавен продукт с ID: {next_id}")
            return str(next_id)
        except PyMongoError as e:
            print(f"Грешка при добавяне: {e}")
            return None
    

    def find_product_by_id(self, id: int) -> dict:
        try:
            numeric_id = int(id)
            return self.products.find_one({"_id": numeric_id})
        except ValueError:
            print("ID трябва да бъде число")
            return None
    
    def find_products_by_name(self, name: str) -> list:
        query = {"title": {"$regex": name, "$options": "i"}}
        return list(self.products.find(query))
    
    def find_products_by_brand(self, brand: str) -> list:
        query = {"brand": {"$regex": brand, "$options": "i"}}
        return list(self.products.find(query))
    
    def find_products_by_category(self, category_name: str) -> list:
        category = self.categories.find_one({"name": {"$regex": category_name, "$options": "i"}})
        if not category:
            print(f"Категория '{category_name}' не съществува")
            return []
        return list(self.products.find({"category_id": category["_id"]}))
    
    def fulltext_search(self, search_term: str) -> list:
        if not search_term:
            return []
    
        pipeline = [
            {"$match": {"$text": {"$search": search_term}}},
            {"$addFields": {"score": {"$meta": "textScore"}}},
            {"$sort": {"score": -1}},
            {"$lookup": {
                "from": "categories",
                "localField": "category_id",
                "foreignField": "_id",
                "as": "category"
            }},
            {"$project": {
                "title": 1,
                "brand": 1,
                "price": 1,
                "rating": 1,
                "score": 1,
                "category_name": {"$arrayElemAt": ["$category.name", 0]}
            }}
        ]
        return list(self.products.aggregate(pipeline))

    def get_all_products(self) -> list:
        return list(self.products.find())
    
    def print_product_details(self, product: dict):
        if not product:
            print("Няма данни за продукт")
            return
        
        category = self.categories.find_one({"_id": product["category_id"]})
        cat_name = category["name"] if category else "Unknown"
        
        print("\n" + "="*50)
        print(f"ID: {product['_id']}")
        print(f"Продукт: {product['title']}")
        print(f"Бранд: {product['brand']}")
        print(f"Категория: {cat_name}")
        print(f"Цена: {product['price']} лв.")
        if product.get('discount_price'):
            print(f"Промоция: {product['discount_price']} лв.")
        print(f"Рейтинг: {product.get('rating', 'N/A')}")
        print(f"Наличен: {'Да' if product.get('in_stock') else 'Не'}")
        print("="*50)
    

    def update_product(self, id: int, **updates):
        try:
            numeric_id = int(id)
            product = self.products.find_one({"_id": numeric_id})
            if not product:
                print(f"Продукт с ID {id} не съществува")
                return
            
            update_data = {}
            for key, value in updates.items():
                if value is not None and value != "":
                    update_data[key] = value
            
            if not update_data:
                print("Няма промени за обновяване")
                return
            
            result = self.products.update_one({"_id": numeric_id}, {"$set": update_data})
            print(f"Обновен {result.modified_count} продукт. Променени полета: {list(update_data.keys())}")
        except ValueError:
            print("ID трябва да бъде число")
        except Exception as e:
            print(f"Грешка: {e}")
    

    def delete_product_by_id(self, id: int):
        try:
            numeric_id = int(id)
            
            product = self.products.find_one({"_id": numeric_id})
            if not product:
                print(f"Продукт с ID {id} не съществува")
                return
            
            variants_deleted = self.variants.delete_many({"product_id": numeric_id})
            if variants_deleted.deleted_count > 0:
                print(f"Изтрити {variants_deleted.deleted_count} варианта")
            
            result = self.products.delete_one({"_id": numeric_id})
            if result.deleted_count > 0:
                print(f"Изтрит продукт с ID {id}")
            else:
                print(f"Продукт с ID {id} не може да бъде изтрит")
        except ValueError:
            print("ID трябва да бъде число")
        except Exception as e:
            print(f"Грешка: {e}")
    

    def aggregate_top_10_most_expensive(self) -> list:
        pipeline = [
            {"$sort": {"price": -1}},
            {"$limit": 10},
            {"$lookup": {
                "from": "categories",
                "localField": "category_id",
                "foreignField": "_id",
                "as": "category"
            }},
            {"$project": {
                "title": 1,
                "brand": 1,
                "price": 1,
                "rating": 1,
                "category_name": {"$arrayElemAt": ["$category.name", 0]}
            }}
        ]
        return list(self.products.aggregate(pipeline))
    
    def aggregate_top_10_cheapest(self) -> list:
        pipeline = [
            {"$sort": {"price": 1}},
            {"$limit": 10},
            {"$lookup": {
                "from": "categories",
                "localField": "category_id",
                "foreignField": "_id",
                "as": "category"
            }},
            {"$project": {
                "title": 1,
                "brand": 1,
                "price": 1,
                "rating": 1,
                "category_name": {"$arrayElemAt": ["$category.name", 0]}
            }}
        ]
        return list(self.products.aggregate(pipeline))
    
    def aggregate_products_per_category(self) -> list:
        pipeline = [
            {"$group": {
                "_id": "$category_id",
                "product_count": {"$sum": 1},
                "avg_price": {"$avg": "$price"},
                "avg_rating": {"$avg": "$rating"}
            }},
            {"$lookup": {
                "from": "categories",
                "localField": "_id",
                "foreignField": "_id",
                "as": "category"
            }},
            {"$unwind": "$category"},
            {"$project": {
                "category_name": "$category.name",
                "product_count": 1,
                "avg_price": {"$round": ["$avg_price", 2]},
                "avg_rating": {"$round": ["$avg_rating", 2]}
            }},
            {"$sort": {"product_count": -1}}
        ]
        return list(self.products.aggregate(pipeline))
    
    def aggregate_stats_by_color(self) -> list:
        pipeline = [
            {"$lookup": {
                "from": "variants",
                "localField": "_id",
                "foreignField": "product_id",
                "as": "variants"
            }},
            {"$unwind": "$variants"},
            {"$group": {
                "_id": "$variants.color",
                "total_stock": {"$sum": "$variants.stock"},
                "total_products": {"$sum": 1},
                "unique_brands": {"$addToSet": "$brand"}
            }},
            {"$project": {
                "color": "$_id",
                "total_stock": 1,
                "total_products": 1,
                "brands_count": {"$size": "$unique_brands"}
            }},
            {"$sort": {"total_products": -1}}
        ]
        return list(self.products.aggregate(pipeline))



def print_menu():
    print("\n" + "="*50)
    print("E-COMMERCE PRODUCT CATALOG")
    print("="*50)
    print("1. Добави нов продукт")
    print("2. Търси продукт по ID")
    print("3. Търси продукти по име")
    print("4. Търси продукти по бранд")
    print("5. Търси продукти по категория")
    print("6. FULL-TEXT SEARCH")
    print("7. Всички продукти")
    print("8. Обнови продукт")
    print("9. Изтрий продукт")
    print("-" * 50)
    print("10. Топ 10 най-скъпи продукта")
    print("11. Топ 10 най-евтини продукта")
    print("12. Брой продукти по категории")
    print("13. Статистика по цветове")
    print("-" * 50)
    print("0. Изход")
    print("="*50)


if __name__ == "__main__":
    store = ECommerceStore()
    
    while True:
        print_menu()
        choice = input("Избери опция: ")
        
        if choice == '1':
            print("\n--- ДОБАВЯНЕ НА НОВ ПРОДУКТ ---")
            title = input("Заглавие: ")
            brand = input("Бранд: ")
            
            print("\nНалични категории:")
            cats = list(store.categories.find())
            for cat in cats:
                print(f"  {cat['_id']}. {cat['name']}")
            
            try:
                cat_id = int(input("ID на категория: "))
                price = float(input("Цена: "))
                rating_input = input("Рейтинг (1-5): ")
                rating = float(rating_input) if rating_input else 3.0
                
                store.add_product(title, brand, cat_id, price, rating)
            except ValueError:
                print("Невалиден вход! Моля въведете числа където се изисква.")
        
        elif choice == '2':
            prod_id = input("ID на продукт: ")
            try:
                product = store.find_product_by_id(int(prod_id))
                store.print_product_details(product)
            except ValueError:
                print("ID трябва да бъде число")
        
        elif choice == '3':
            name = input("Име: ")
            products = store.find_products_by_name(name)
            print(f"\nНамерени {len(products)} продукта:")
            for p in products:
                print(f"   {p['title']} - {p['brand']} - {p['price']} лв.")
        
        elif choice == '4':
            brand = input("Бранд: ")
            products = store.find_products_by_brand(brand)
            print(f"\nНамерени {len(products)} продукта от {brand}:")
            for p in products:
                print(f"   {p['title']} - {p['price']} лв. {p.get('rating', 'N/A')}")
        
        elif choice == '5':
            cat_name = input("Име на категория: ")
            products = store.find_products_by_category(cat_name)
            if products:
                print(f"\nНамерени {len(products)} продукта в категорията:")
                for p in products:
                    print(f"   {p['title']} - {p['brand']} - {p['price']} лв.")
        
        elif choice == '6':
            search_term = input("Въведете дума за търсене: ")
            results = store.fulltext_search(search_term)
            print(f"\nНамерени {len(results)} резултата за '{search_term}':")
            print("-" * 50)
            for i, p in enumerate(results, 1):
                print(f"{i}. {p['title']} - {p['brand']} - {p['price']} лв. ({p['rating']})")
                print(f"   Категория: {p['category_name']} | Релевантност: {p['score']:.2f}")
                print()

        elif choice == '7':
            products = store.get_all_products()
            print(f"\nВСИЧКИ ПРОДУКТИ ({len(products)} бр.):")
            print("="*60)
            for p in products:
                print(f"   [{p['_id']}] {p['title']} - {p['brand']} - {p['price']} лв. {p.get('rating', 'N/A')}")
            print("="*60)
            input("\nНатисни Enter за да продължиш...")
        
        elif choice == '8':
            try:
                prod_id = int(input("ID на продукт за обновяване: "))
                product = store.find_product_by_id(prod_id)
                if not product:
                    continue
                
                store.print_product_details(product)
                print("\n--- ОСТАВЕТЕ ПРАЗНО ЗА ДА НЕ ПРОМЕНЯТЕ ---")
                new_title = input(f"Ново заглавие (беше: {product['title']}): ") or None
                new_brand = input(f"Нов бранд (беше: {product['brand']}): ") or None
                new_price = input(f"Нова цена (беше: {product['price']}): ") or None
                new_rating = input(f"Нов рейтинг (беше: {product.get('rating', 'N/A')}): ") or None
                
                updates = {}
                if new_title:
                    updates["title"] = new_title
                if new_brand:
                    updates["brand"] = new_brand
                if new_price:
                    updates["price"] = float(new_price)
                if new_rating:
                    updates["rating"] = float(new_rating)
                
                store.update_product(prod_id, **updates)
            except ValueError:
                print("ID трябва да бъде число")
        
        elif choice == '9':
            try:
                prod_id = int(input("ID на продукт за изтриване: "))
                confirm = input(f"Сигурни ли сте, че искате да изтриете продукт {prod_id}? (y/n): ")
                if confirm.lower() == 'y':
                    store.delete_product_by_id(prod_id)
            except ValueError:
                print("ID трябва да бъде число")
        
        elif choice == '10':
            print("\nТОП 10 НАЙ-СКЪПИ ПРОДУКТА:")
            print("-" * 50)
            results = store.aggregate_top_10_most_expensive()
            for i, p in enumerate(results, 1):
                print(f"{i}. {p['title']} - {p['brand']} - {p['price']} лв. ({p['rating']})")
        
        elif choice == '11':
            print("\nТОП 10 НАЙ-ЕВТИНИ ПРОДУКТА:")
            print("-" * 50)
            results = store.aggregate_top_10_cheapest()
            for i, p in enumerate(results, 1):
                print(f"{i}. {p['title']} - {p['brand']} - {p['price']} лв. ({p['rating']})")
        
        elif choice == '12':
            print("\nБРОЙ ПРОДУКТИ ПО КАТЕГОРИИ:")
            print("-" * 50)
            results = store.aggregate_products_per_category()
            for cat in results:
                print(f"{cat['category_name']}: {cat['product_count']} продукта (ср.цена: {cat['avg_price']} лв.)")
        
        elif choice == '13':
            print("\nСТАТИСТИКА ПО ЦВЕТОВЕ:")
            print("-" * 50)
            results = store.aggregate_stats_by_color()
            for color in results:
                if color['color']:
                    print(f"{color['color']}: {color['total_products']} продукта, {color['total_stock']} бр. наличност")
        
        elif choice == '0':
            store.close_connection()
            print("Благодаря за използването! Довиждане!")
            break
        
        else:
            print("Невалиден избор! Моля опитайте отново.")