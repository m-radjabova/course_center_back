from database import get_connection

class ShopService:
    
    def create_shop(self, shop_name: str, owner_name: str = None, phone_number: str = None, address: str = None):
        connect = get_connection()
        cursor = connect.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO shop (shop_name, owner_name, phone_number, address)
                VALUES (%s, %s, %s, %s)
                RETURNING shop_id
                """,
                (shop_name, owner_name, phone_number, address)
            )
            shop_id = cursor.fetchone()["shop_id"]
            connect.commit()
            return {"success": True, "shop_id": shop_id}
        except Exception as e:
            connect.rollback()
            return {"success": False, "message": str(e)}
        finally:
            cursor.close()
            connect.close()
    
    def get_shop_by_id(self, shop_id: int):
        connect = get_connection()
        cursor = connect.cursor()
        try:
            cursor.execute(
                """
                SELECT shop_id, shop_name, owner_name, phone_number, address, is_active
                FROM shop
                WHERE shop_id = %s
                """,
                (shop_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            connect.close()
    
    def get_all_shops(self):
        connect = get_connection()
        cursor = connect.cursor()
        try:
            cursor.execute(
                """
                SELECT shop_id, shop_name, owner_name, phone_number, is_active, address
                FROM shop
                WHERE is_active = TRUE
                ORDER BY shop_name
                """
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            connect.close()
    
    def update_shop(self, shop_id: int, shop_name: str = None, owner_name: str = None, 
                   phone_number: str = None, address: str = None):
        connect = get_connection()
        cursor = connect.cursor()
        try:
            updates = []
            values = []
            
            if shop_name:
                updates.append("shop_name = %s")
                values.append(shop_name)
            if owner_name:
                updates.append("owner_name = %s")
                values.append(owner_name)
            if phone_number:
                updates.append("phone_number = %s")
                values.append(phone_number)
            if address:
                updates.append("address = %s")
                values.append(address)
            
            if not updates:
                return {"success": False, "message": "No fields to update"}
            
            values.append(shop_id)
            query = f"UPDATE shop SET {', '.join(updates)} WHERE shop_id = %s"
            
            cursor.execute(query, values)
            connect.commit()
            return {"success": True, "message": "Do'kon yangilandi"}
        except Exception as e:
            connect.rollback()
            return {"success": False, "message": str(e)}
        finally:
            cursor.close()
            connect.close()


    def get_shop_by_name(self, shop_name: str):
        connect = get_connection()
        cursor = connect.cursor()
        try:
            cursor.execute(
                """
                SELECT shop_id, shop_name, owner_name, phone_number, address, is_active
                FROM shop
                WHERE shop_name ILIKE %s AND is_active = TRUE
                """,
                (f"%{shop_name}%",)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            connect.close()
    
    def search_shops_by_name(self, shop_name: str):
        connect = get_connection()
        cursor = connect.cursor()
        try:
            cursor.execute(
                """
                SELECT shop_id, shop_name, owner_name, phone_number, is_active
                FROM shop
                WHERE shop_name ILIKE %s AND is_active = TRUE
                ORDER BY shop_name
                """,
                (f"%{shop_name}%",)
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            connect.close()