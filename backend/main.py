from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import os
import pymysql
from pymysql.cursors import DictCursor

app = FastAPI(title="Medicine Inventory API")

# CORS middleware to allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class Medicine(BaseModel):
    name: str
    quantity: int
    expiry_date: date
    category: str

class MedicineResponse(BaseModel):
    id: int
    name: str
    quantity: int
    expiry_date: date
    category: str

# Database connection
def get_db():
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "medicine_inventory"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "password"),
            port=int(os.getenv("DB_PORT", "3306")),
            cursorclass=DictCursor,
            ssl={'ssl': False}  # Disable SSL for AWS RDS MariaDB
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

# Health endpoint (required)
@app.get("/health")
def health():
    return {"status": "healthy", "service": "medicine-inventory-backend"}

# Get all medicines
@app.get("/api/medicines", response_model=List[MedicineResponse])
def get_medicines():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM medicines ORDER BY id")
        medicines = cur.fetchall()
        cur.close()
        conn.close()
        return medicines
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Get specific medicine
@app.get("/api/medicines/{medicine_id}", response_model=MedicineResponse)
def get_medicine(medicine_id: int):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM medicines WHERE id = %s", (medicine_id,))
        medicine = cur.fetchone()
        cur.close()
        conn.close()
        
        if medicine is None:
            raise HTTPException(status_code=404, detail="Medicine not found")
        
        return medicine
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Add new medicine
@app.post("/api/medicines", response_model=MedicineResponse, status_code=201)
def add_medicine(medicine: Medicine):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO medicines (name, quantity, expiry_date, category)
            VALUES (%s, %s, %s, %s)
            """,
            (medicine.name, medicine.quantity, medicine.expiry_date, medicine.category)
        )
        conn.commit()
        
        # Get the inserted record
        medicine_id = cur.lastrowid
        cur.execute("SELECT * FROM medicines WHERE id = %s", (medicine_id,))
        new_medicine = cur.fetchone()
        
        cur.close()
        conn.close()
        return new_medicine
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Root endpoint
@app.get("/")
def root():
    return {
        "message": "Medicine Inventory API",
        "endpoints": {
            "health": "/health",
            "medicines": "/api/medicines",
            "medicine_by_id": "/api/medicines/{id}"
        }
    }