from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
from enum import Enum
import random

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="IoT Home Automation System", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Global connection manager for WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# Enums and Models
class DeviceType(str, Enum):
    RELAY = "relay"
    SWITCH = "switch"
    SENSOR = "sensor"

class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"

class RelayState(str, Enum):
    ON = "on"
    OFF = "off"

class ScheduleType(str, Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"

class Device(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    device_type: DeviceType
    room: str
    gpio_pin: Optional[int] = None
    status: DeviceStatus = DeviceStatus.OFFLINE
    relay_state: RelayState = RelayState.OFF
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    wifi_signal: Optional[int] = None
    uptime: int = 0  # in seconds
    total_runtime: int = 0  # total on-time in seconds

class DeviceCreate(BaseModel):
    name: str
    device_type: DeviceType = DeviceType.RELAY
    room: str
    gpio_pin: Optional[int] = 18

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    room: Optional[str] = None
    gpio_pin: Optional[int] = None

class RelayControl(BaseModel):
    device_id: str
    state: RelayState

class Schedule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str
    name: str
    schedule_type: ScheduleType
    target_state: RelayState
    trigger_time: str  # HH:MM format
    trigger_date: Optional[datetime] = None  # for ONCE type
    days_of_week: Optional[List[int]] = None  # 0=Monday, 6=Sunday for WEEKLY
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ScheduleCreate(BaseModel):
    device_id: str
    name: str
    schedule_type: ScheduleType
    target_state: RelayState
    trigger_time: str
    trigger_date: Optional[datetime] = None
    days_of_week: Optional[List[int]] = None

class DeviceLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str
    action: str
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    triggered_by: str = "manual"  # manual, schedule, api
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Device Simulator Class
class DeviceSimulator:
    def __init__(self):
        self.devices: Dict[str, Dict] = {}
        self.running = False
    
    async def start(self):
        if not self.running:
            self.running = True
            asyncio.create_task(self.simulate_devices())
    
    async def stop(self):
        self.running = False
    
    async def add_device(self, device: Device):
        """Add a device to simulation"""
        self.devices[device.id] = {
            "device": device,
            "last_state_change": datetime.utcnow(),
            "simulation_data": {
                "wifi_signal": random.randint(50, 100),
                "response_time": random.uniform(0.1, 0.5)
            }
        }
    
    async def remove_device(self, device_id: str):
        """Remove device from simulation"""
        if device_id in self.devices:
            del self.devices[device_id]
    
    async def control_relay(self, device_id: str, state: RelayState) -> bool:
        """Simulate relay control with realistic delays"""
        if device_id not in self.devices:
            return False
        
        # Simulate network delay
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        device_data = self.devices[device_id]
        old_state = device_data["device"].relay_state
        device_data["device"].relay_state = state
        device_data["device"].last_seen = datetime.utcnow()
        device_data["last_state_change"] = datetime.utcnow()
        
        # Update database
        await db.devices.update_one(
            {"id": device_id},
            {
                "$set": {
                    "relay_state": state.value,
                    "last_seen": datetime.utcnow()
                }
            }
        )
        
        # Log the action
        log_entry = DeviceLog(
            device_id=device_id,
            action=f"relay_control",
            old_state=old_state.value,
            new_state=state.value,
            triggered_by="manual"
        )
        await db.device_logs.insert_one(log_entry.dict())
        
        # Broadcast the change
        await manager.broadcast(json.dumps({
            "type": "device_update",
            "device_id": device_id,
            "data": {
                "relay_state": state.value,
                "last_seen": datetime.utcnow().isoformat()
            }
        }))
        
        return True
    
    async def simulate_devices(self):
        """Main simulation loop"""
        while self.running:
            try:
                for device_id, device_data in self.devices.items():
                    device = device_data["device"]
                    
                    # Simulate uptime
                    device.uptime += 5
                    
                    # Simulate occasional connectivity issues
                    if random.random() < 0.01:  # 1% chance per cycle
                        device.status = DeviceStatus.OFFLINE
                    else:
                        device.status = DeviceStatus.ONLINE
                    
                    # Update wifi signal strength
                    device_data["simulation_data"]["wifi_signal"] = max(30, 
                        device_data["simulation_data"]["wifi_signal"] + random.randint(-5, 5))
                    device.wifi_signal = device_data["simulation_data"]["wifi_signal"]
                    
                    # Update total runtime if relay is on
                    if device.relay_state == RelayState.ON:
                        device.total_runtime += 5
                    
                    device.last_seen = datetime.utcnow()
                    
                    # Update database
                    await db.devices.update_one(
                        {"id": device_id},
                        {
                            "$set": {
                                "status": device.status.value,
                                "uptime": device.uptime,
                                "total_runtime": device.total_runtime,
                                "wifi_signal": device.wifi_signal,
                                "last_seen": device.last_seen
                            }
                        }
                    )
                
                # Send periodic status updates
                if self.devices:
                    devices_status = []
                    for device_id, device_data in self.devices.items():
                        device = device_data["device"]
                        devices_status.append({
                            "id": device.id,
                            "status": device.status.value,
                            "relay_state": device.relay_state.value,
                            "uptime": device.uptime,
                            "wifi_signal": device.wifi_signal,
                            "last_seen": device.last_seen.isoformat()
                        })
                    
                    await manager.broadcast(json.dumps({
                        "type": "status_update",
                        "devices": devices_status
                    }))
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logging.error(f"Simulation error: {e}")
                await asyncio.sleep(5)

# Global device simulator
device_simulator = DeviceSimulator()

# Scheduler Class
class TaskScheduler:
    def __init__(self):
        self.running = False
    
    async def start(self):
        if not self.running:
            self.running = True
            asyncio.create_task(self.scheduler_loop())
    
    async def stop(self):
        self.running = False
    
    async def scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                # Get all active schedules
                schedules = await db.schedules.find({"is_active": True}).to_list(None)
                
                for schedule_data in schedules:
                    schedule = Schedule(**schedule_data)
                    
                    if await self.should_trigger(schedule, current_time):
                        await self.execute_schedule(schedule)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logging.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
    
    async def should_trigger(self, schedule: Schedule, current_time: datetime) -> bool:
        """Check if schedule should trigger"""
        trigger_time_parts = schedule.trigger_time.split(":")
        trigger_hour = int(trigger_time_parts[0])
        trigger_minute = int(trigger_time_parts[1])
        
        # Check if current time matches trigger time (within 1 minute window)
        if (current_time.hour == trigger_hour and 
            current_time.minute == trigger_minute):
            
            if schedule.schedule_type == ScheduleType.ONCE:
                if schedule.trigger_date:
                    return (current_time.date() == schedule.trigger_date.date())
            
            elif schedule.schedule_type == ScheduleType.DAILY:
                return True
            
            elif schedule.schedule_type == ScheduleType.WEEKLY:
                if schedule.days_of_week:
                    return current_time.weekday() in schedule.days_of_week
        
        return False
    
    async def execute_schedule(self, schedule: Schedule):
        """Execute a scheduled task"""
        try:
            # Control the device
            success = await device_simulator.control_relay(
                schedule.device_id, 
                schedule.target_state
            )
            
            if success:
                # Log the scheduled action
                log_entry = DeviceLog(
                    device_id=schedule.device_id,
                    action=f"scheduled_control",
                    new_state=schedule.target_state.value,
                    triggered_by=f"schedule:{schedule.name}"
                )
                await db.device_logs.insert_one(log_entry.dict())
                
                # If this was a ONCE schedule, deactivate it
                if schedule.schedule_type == ScheduleType.ONCE:
                    await db.schedules.update_one(
                        {"id": schedule.id},
                        {"$set": {"is_active": False}}
                    )
                
                logging.info(f"Executed schedule '{schedule.name}' for device {schedule.device_id}")
            
        except Exception as e:
            logging.error(f"Failed to execute schedule {schedule.id}: {e}")

# Global scheduler
task_scheduler = TaskScheduler()

# API Routes

@api_router.get("/")
async def root():
    return {"message": "IoT Home Automation System API", "version": "1.0.0"}

# Device Management Routes
@api_router.post("/devices", response_model=Device)
async def create_device(device_input: DeviceCreate):
    """Create a new IoT device"""
    device = Device(**device_input.dict())
    device.ip_address = f"192.168.1.{random.randint(100, 200)}"
    device.status = DeviceStatus.ONLINE
    
    # Insert into database
    result = await db.devices.insert_one(device.dict())
    
    # Add to simulator
    await device_simulator.add_device(device)
    
    return device

@api_router.get("/devices", response_model=List[Device])
async def get_devices():
    """Get all devices"""
    devices = await db.devices.find().to_list(None)
    return [Device(**device) for device in devices]

@api_router.get("/devices/{device_id}", response_model=Device)
async def get_device(device_id: str):
    """Get a specific device"""
    device = await db.devices.find_one({"id": device_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return Device(**device)

@api_router.put("/devices/{device_id}", response_model=Device)
async def update_device(device_id: str, device_update: DeviceUpdate):
    """Update device information"""
    device = await db.devices.find_one({"id": device_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    update_data = {k: v for k, v in device_update.dict().items() if v is not None}
    if update_data:
        await db.devices.update_one({"id": device_id}, {"$set": update_data})
        device.update(update_data)
    
    return Device(**device)

@api_router.delete("/devices/{device_id}")
async def delete_device(device_id: str):
    """Delete a device"""
    result = await db.devices.delete_one({"id": device_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Remove from simulator
    await device_simulator.remove_device(device_id)
    
    return {"message": "Device deleted successfully"}

# Device Control Routes
@api_router.post("/devices/control")
async def control_device(control: RelayControl):
    """Control a device relay"""
    success = await device_simulator.control_relay(control.device_id, control.state)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found or offline")
    
    return {"message": f"Device {control.device_id} set to {control.state.value}"}

# Scheduling Routes
@api_router.post("/schedules", response_model=Schedule)
async def create_schedule(schedule_input: ScheduleCreate):
    """Create a new schedule"""
    # Verify device exists
    device = await db.devices.find_one({"id": schedule_input.device_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    schedule = Schedule(**schedule_input.dict())
    await db.schedules.insert_one(schedule.dict())
    
    return schedule

@api_router.get("/schedules", response_model=List[Schedule])
async def get_schedules():
    """Get all schedules"""
    schedules = await db.schedules.find().to_list(None)
    return [Schedule(**schedule) for schedule in schedules]

@api_router.get("/schedules/device/{device_id}", response_model=List[Schedule])
async def get_device_schedules(device_id: str):
    """Get schedules for a specific device"""
    schedules = await db.schedules.find({"device_id": device_id}).to_list(None)
    return [Schedule(**schedule) for schedule in schedules]

@api_router.put("/schedules/{schedule_id}", response_model=Schedule)
async def update_schedule(schedule_id: str, schedule_update: ScheduleCreate):
    """Update a schedule"""
    schedule = await db.schedules.find_one({"id": schedule_id})
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    await db.schedules.update_one(
        {"id": schedule_id},
        {"$set": schedule_update.dict()}
    )
    
    updated_schedule = await db.schedules.find_one({"id": schedule_id})
    return Schedule(**updated_schedule)

@api_router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """Delete a schedule"""
    result = await db.schedules.delete_one({"id": schedule_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return {"message": "Schedule deleted successfully"}

@api_router.put("/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: str):
    """Toggle schedule active status"""
    schedule = await db.schedules.find_one({"id": schedule_id})
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    new_status = not schedule.get("is_active", True)
    await db.schedules.update_one(
        {"id": schedule_id},
        {"$set": {"is_active": new_status}}
    )
    
    return {"message": f"Schedule {'activated' if new_status else 'deactivated'}"}

# Logging Routes
@api_router.get("/logs", response_model=List[DeviceLog])
async def get_logs(device_id: Optional[str] = None, limit: int = 100):
    """Get device logs"""
    query = {}
    if device_id:
        query["device_id"] = device_id
    
    logs = await db.device_logs.find(query).sort("timestamp", -1).limit(limit).to_list(None)
    return [DeviceLog(**log) for log in logs]

# Statistics Routes
@api_router.get("/stats")
async def get_system_stats():
    """Get system statistics"""
    total_devices = await db.devices.count_documents({})
    online_devices = await db.devices.count_documents({"status": "online"})
    total_schedules = await db.schedules.count_documents({})
    active_schedules = await db.schedules.count_documents({"is_active": True})
    
    # Get total runtime for all devices
    devices = await db.devices.find().to_list(None)
    total_runtime = sum(device.get("total_runtime", 0) for device in devices)
    
    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": total_devices - online_devices,
        "total_schedules": total_schedules,
        "active_schedules": active_schedules,
        "total_runtime_hours": round(total_runtime / 3600, 2),
        "system_uptime": "24/7"
    }

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Include the router in the main app
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting IoT Home Automation System...")
    
    # Start device simulator
    await device_simulator.start()
    
    # Start task scheduler
    await task_scheduler.start()
    
    # Load existing devices into simulator
    devices = await db.devices.find().to_list(None)
    for device_data in devices:
        device = Device(**device_data)
        await device_simulator.add_device(device)
    
    logger.info("IoT Home Automation System started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down IoT Home Automation System...")
    
    # Stop services
    await device_simulator.stop()
    await task_scheduler.stop()
    
    # Close database connection
    client.close()
    
    logger.info("IoT Home Automation System shutdown complete.")