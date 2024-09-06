from datetime import datetime, time, timedelta
import json
import re
from typing import Annotated, List, Optional
from fastapi import Body, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, BeforeValidator, Field, TypeAdapter
import motor.motor_asyncio
from dotenv import dotenv_values
from bson import ObjectId
from pymongo import ReturnDocument
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

config = dotenv_values(".env")

client = motor.motor_asyncio.AsyncIOMotorClient(config["MONGO_URL"])
db = client.capstone

app = FastAPI()

format = "%Y-%m-%d %H:%M:%S %Z%z"


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PyObjectId = Annotated[str, BeforeValidator(str)]

class current(BaseModel):
    id: Optional[PyObjectId] = Field(alias = "_id", default = None)
    current_limit: Optional[float] = None

class socket(BaseModel):
    id: Optional[PyObjectId] = Field(alias = "_id", default = None)
    socket_state: Optional[bool] = None   
    datetime: Optional[str] = None

class currents(BaseModel):
    id: Optional[PyObjectId] = Field(alias = "_id", default = None)
    amps: Optional[float] = None

class time(BaseModel):
    id: Optional[PyObjectId] = Field(alias = "_id", default = None)
    duration_seconds: Optional[int]
    
#CONTROL OF SOCKET STATE
@app.put("/socketState", status_code=200)
async def setSocketState(socket_info:socket):
   all_settings = await db["socketState"].find().to_list(1)
   entry_time = datetime.now().strftime("%H:%M:%S")
   socket_data = socket_info.model_dump()
   socket_data["datetime"] = entry_time
   
   if len(all_settings) == 1:
       if all_settings[0]["socket_state"] == True:
           start_time = datetime.strptime(all_settings[0]["datetime"], "%H:%M:%S")

           time = datetime.strptime(entry_time, "%H:%M:%S")

           duration = time - start_time
           duration_seconds = duration.total_seconds()

           duration_data = {
                "duration_seconds": duration_seconds
            }
           
           await db["timeUsage"].insert_one(duration_data)

           await db["socketState"].update_one({"_id":all_settings[0]["_id"]},{"$set":socket_data})
           return socket(**socket_data)
            
       else:
           await db["socketState"].update_one({"_id":all_settings[0]["_id"]},{"$set":socket_data})
           created_data = await db["socketState"].find_one({"_id": all_settings[0]["_id"]})
           return socket(**created_data)
       
   else:
        entry_time = datetime.now().strftime("%H:%M:%S")
        socket_data = socket_info.model_dump()
        socket_data["datetime"] = entry_time
        new_settings = await db["socketState"].insert_one(socket_data)
        created_settings = await db["socketState"].find_one({"_id": new_settings.inserted_id})
        final = (socket(**created_settings)).model_dump()
        return JSONResponse(status_code=201, content=final)

@app.get("/socketState", status_code=200)
async def get_state():
    data = await db["socketState"].find().to_list(1)
    return TypeAdapter(List[socket]).validate_python(data)

#CONTROL OF SOCKET CURRENT LIMIT
@app.put("/currentLimit", status_code=200)
async def setCurrentLimit(current_info: current):
    all_settings = await db["currentInfo"].find().to_list(999)
    if len(all_settings)==1:
        db["currentInfo"].update_one({"_id":all_settings[0]["_id"]},{"$set":current_info.model_dump()})
        updated_settings = await db["currentInfo"].find_one({"_id": all_settings[0]["_id"]})
        return current(**updated_settings)
    
    else:
        new_current_info = current_info.model_dump()
        new_data = await db["currentInfo"].insert_one(new_current_info)
        created_data = await db["currentInfo"].find_one({"_id": new_data.inserted_id})
        return current(**created_data)
    
@app.put("/webSocketState", status_code=200)
async def setWebSocketState(socket_info: socket):
    all_settings = await db["webSocketState"].find().to_list(999)
    if len(all_settings)==1:
        db["webSocketState"].update_one({"_id":all_settings[0]["_id"]},{"$set":socket_info.model_dump()})
        updated_settings = await db["webSokcetState"].find_one({"_id": all_settings[0]["_id"]})
        return socket(**updated_settings)
    
    else:
        new_socket_info = socket_info.model_dump()
        new_data = await db["webSocketState"].insert_one(new_socket_info)
        created_data = await db["webSocketState"].find_one({"_id": new_data.inserted_id})
        return socket(**created_data)

@app.get("/currentLimit", status_code=200)
async def get_current_limit():
    data = await db["currentInfo"].find().to_list(1)
    return TypeAdapter(List[current]).validate_python(data)

#CURRENT VALUES SENT FROM ESP32
@app.post("/currentValues", status_code=201)
async def createCurrent(current: currents):
    new_current = current.model_dump()
    new_data = await db["currentValues"].insert_one(new_current)
    created_data = await db["currentValues"].find_one({"_id": new_data.inserted_id})
    return currents(**created_data)

@app.get("/currentValues", status_code=200)
async def get_data():
    data = await db["currentValues"].find().to_list(999)
    return TypeAdapter(List[currents]).validate_python(data)

@app.get("/duration", status_code=200)
async def get_duration():
    data = await db["timeUsage"].find().to_list(999)
    return TypeAdapter(List[time]).validate_python(data)



