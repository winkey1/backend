from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from dotenv import load_dotenv
import os
from fastapi import Path

app = FastAPI()

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

class Layanan(BaseModel):
    nama: str
    harga_per_kg: int

class Order(BaseModel):
    id: str
    nama: str
    layanan: str
    total: int
    status: str
    created_at: str  
    weight: float | None  


class MonthlyIncome(BaseModel):
    year: int
    month: int
    monthly_income: int

class UpdateStatus(BaseModel):
    status: str

class CreateOrder(BaseModel):
    order_code: str
    nama: str
    layanan: str   
    weight: float
    price: int
    status: str

@app.get("/orders", response_model=list[Order])
def get_orders():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Fetch all the necessary columns from the orders table
    cur.execute("""
        SELECT id, nama, layanan, total, status, created_at, weight 
        FROM orders 
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": row[0],
            "nama": row[1],
            "layanan": row[2],
            "total": row[3],
            "status": row[4],
            "created_at": row[5].isoformat() if row[5] else None,  # Optional date formatting
            "weight": row[6],
        }
        for row in rows
    ]

@app.post("/orders")
def create_order(order: CreateOrder):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (id, nama, weight, total, status, layanan)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (order.order_code, order.nama, order.weight, order.price, order.status, order.layanan),
        )
        inserted_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Order berhasil disimpan", "order_id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan order: {str(e)}")

@app.put("/orders/{order_id}")
def update_order_status(order_id: str, update: UpdateStatus):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE id = %s RETURNING id", (update.status, order_id))
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if result:
        return {"message": "Status berhasil diperbarui"}
    else:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")

@app.get("/monthly_income", response_model=list[MonthlyIncome])
def get_monthly_income():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # SQL query to calculate monthly income
        cur.execute("""
            SELECT EXTRACT(YEAR FROM created_at) AS year,
                   EXTRACT(MONTH FROM created_at) AS month,
                   SUM(total) AS monthly_income
            FROM orders
            WHERE status = 'Selesai'  
            GROUP BY year, month
            ORDER BY year DESC, month DESC
        """)
        
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Return the results as a list of dictionaries
        return [
            {
                "year": int(row[0]),
                "month": int(row[1]),
                "monthly_income": int(row[2]),
            }
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch monthly income data: {str(e)}")
    
@app.delete("/orders/{order_id}")
def delete_order(order_id: str = Path(..., description="ID dari order yang akan dihapus")):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("DELETE FROM orders WHERE id = %s RETURNING id", (order_id,))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result:
            return {"message": "Order berhasil dihapus"}
        else:
            raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menghapus order: {str(e)}")

@app.get("/layanan")
def get_layanan():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id, nama, harga_per_kg FROM layanan ORDER BY id ASC")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {"id": row[0], "nama": row[1], "harga_per_kg": row[2]}
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data layanan: {str(e)}")

@app.post("/layanan", status_code=201)
def create_layanan(layanan: Layanan):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO layanan (nama, harga_per_kg) VALUES (%s, %s) RETURNING id",
            (layanan.nama, layanan.harga_per_kg)
        )
        layanan_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Layanan berhasil ditambahkan", "id": layanan_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menambahkan layanan: {str(e)}")


@app.get("/order/{order_id}", response_model=Order)
def get_order(order_id: str = Path(..., description="ID dari order")):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query = """
            SELECT id, nama, layanan, total, status, created_at, weight
            FROM orders
            WHERE id = %s
        """
        cursor.execute(query, (order_id,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if not result:
            raise HTTPException(status_code=404, detail="Order not found")

        return {
            "id": result[0],
            "nama": result[1],
            "layanan": result[2],
            "total": result[3],
            "status": result[4],
            "created_at": result[5].isoformat(),
            "weight": result[6],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
