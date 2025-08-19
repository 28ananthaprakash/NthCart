from fastapi import FastAPI
from handlers import router as handlers_router

app = FastAPI()

app.include_router(handlers_router) # Loading handlers and routes

