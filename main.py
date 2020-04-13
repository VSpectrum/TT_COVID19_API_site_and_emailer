from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
import redis, config
from collections import OrderedDict
from fastapi.middleware.cors import CORSMiddleware
from email_validator import validate_email, EmailNotValidError
import pickle

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="templates")

conn = redis.StrictRedis(config.redis_uri, password=config.redis_passwd)

@app.get("/all")
async def get_all():
    data = {}
    for key in conn.keys():
        data[key] = conn.hgetall(key)
    return OrderedDict(sorted(data.items(), reverse=True))

@app.get("/")
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request,})

@app.get("/subscribe")
async def subscribe_email(request: Request):
    return templates.TemplateResponse("sub.html", {"request": request,})

@app.get("/subscribe/")
async def subscribe_email(email: str, request: Request):
    try:
        v_email = validate_email(email) # validate and get info
        v_email = v_email["email"]
        try:
            email_list = pickle.load(open("email_list.pkl", "rb"))
            email_list.add(v_email)
            pickle.dump(email_list, open("email_list.pkl", "wb"))
        except (OSError, IOError) as e:
            pickle.dump({v_email}, open("email_list.pkl", "wb"))
        return f"Successfully added {v_email} to email list."
    except EmailNotValidError as e:
        return str(e)

@app.get("/unsubscribe/")
async def unsubscribe_email(email: str, request: Request):
    try:
        v_email = validate_email(email) # validate and get info
        v_email = v_email["email"]
        try:
            email_list = pickle.load(open("email_list.pkl", "rb"))
            email_list.remove(v_email)
            pickle.dump(email_list, open("email_list.pkl", "wb"))
        except (OSError, IOError) as e:
            pass
        return f"Successfully removed {v_email} from email list."
    except EmailNotValidError as e:
        return str(e)
