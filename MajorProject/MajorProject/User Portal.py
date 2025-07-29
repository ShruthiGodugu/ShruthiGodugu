import os
import gridfs
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL Connection
DATABASE_URL = os.getenv("DB_URL")


mongo_uri = os.getenv("MONGO_URI")
mongo_db = os.getenv("MONGO_DB")
# MongoDB Connection

client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
db = client[mongo_db]
fs = gridfs.GridFS(db)  # Initialize GridFS for video storage

# Initialize FastAPI
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates for rendering HTML pages
templates = Jinja2Templates(directory="templates")

# -------------------------------
# ✅ PostgreSQL Connection
# -------------------------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# -------------------------------
# ✅ Serve Dashboard (Login Page)
# -------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# -------------------------------
# ✅ Handle Login 
# -------------------------------
from fastapi.responses import RedirectResponse

@app.post("/login")
async def login(user_id: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM users WHERE user_id = %s AND password = %s", (user_id, password))
        user = cur.fetchone()
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Database error", "error": str(e)})
    finally:
        cur.close()
        conn.close()

    if user:
        print(f"✅ User '{user_id}' logged in successfully!")
        return JSONResponse(status_code=200, content={"message": "Login successful", "status": "success", "redirect": "/videos"})
    else:
        print("❌ Invalid login attempt!")
        return JSONResponse(status_code=401, content={"message": "Invalid credentials", "status": "failed"})

# -------------------------------
# ✅ Stream Video from GridFS
# -------------------------------
@app.get("/videos", response_class=HTMLResponse)
async def show_videos(request: Request):
    try:
        # Fetch all videos with their upload time
        video_files = list(db.fs.files.find({}, {"_id": 1, "filename": 1, "uploadDate": 1}))

        # Convert uploadDate to a readable format
        for video in video_files:
            video["uploadDate"] = video["uploadDate"].strftime("%Y-%m-%d %H:%M:%S")

        return templates.TemplateResponse("videos.html", {"request": request, "videos": video_files})

    except Exception as e:
        print("❌ Database error:", str(e))
        return JSONResponse(status_code=500, content={"message": "Database error", "error": str(e)})



@app.get("/video/{video_id}")
async def get_video(video_id: str):
    try:
        file_id = ObjectId(video_id)  # Convert string ID to ObjectId
        grid_out = fs.get(file_id)    # Retrieve video from GridFS

        def file_generator():
            while chunk := grid_out.read(1024):  # Read video in chunks
                yield chunk

        return StreamingResponse(file_generator(), media_type="video/mp4")

    except Exception as e:
        print(f"❌ Error fetching video {video_id}:", str(e))
        raise HTTPException(status_code=404, detail="Video not found")


# -------------------------------
# ✅ Run FastAPI Server
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
