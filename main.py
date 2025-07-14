from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, date, time
import asyncio
import threading
import logging
from services import (
    create_complaint, get_complaint_by_id, get_complaints_by_date,
    update_complaint, delete_complaint, delete_complaint_media,
    upload_file_thread
)

app = FastAPI(
    title="Rail Sathi Complaint API",
    description="API for handling rail complaints",
    version="1.0.0",
    openapi_url="/rs_microservice/openapi.json",  # Add the prefix here
    docs_url="/rs_microservice/docs",             # Add the prefix here
    redoc_url="/rs_microservice/redoc"            # Add the prefix here (optional)
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database import get_db_connection
from psycopg2.extras import RealDictCursor


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/rs_microservice")
async def root():
    return {"message": "Rail Sathi Microservice is running"}


class RailSathiComplainMediaResponse(BaseModel):
    id: int
    media_type: Optional[str]
    media_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]

# Separate the complaint data model
class RailSathiComplainData(BaseModel):
    complain_id: int
    pnr_number: Optional[str]
    is_pnr_validated: Optional[str]
    name: Optional[str]
    mobile_number: Optional[str]
    complain_type: Optional[str]
    complain_description: Optional[str]
    complain_date: Optional[date]
    complain_status: str
    train_id: Optional[int]
    train_number: Optional[str]
    train_name: Optional[str]
    coach: Optional[str]
    berth_no: Optional[int]
    created_at: datetime
    created_by: Optional[str]
    updated_at: datetime
    updated_by: Optional[str]
    # Add the missing fields from your actual data
    train_no: Optional[int]
    train_depot: Optional[str]
    rail_sathi_complain_media_files: List[RailSathiComplainMediaResponse]

# Response wrapper that matches your actual API response structure
class RailSathiComplainResponse(BaseModel):
    message: str
    data: RailSathiComplainData

# Alternative: If you want to keep the flat structure, modify your endpoint to return:
class RailSathiComplainFlatResponse(BaseModel):
    message: str
    complain_id: int
    pnr_number: Optional[str]
    is_pnr_validated: Optional[str]
    name: Optional[str]
    mobile_number: Optional[str]
    complain_type: Optional[str]
    complain_description: Optional[str]
    complain_date: Optional[date]
    complain_status: str
    train_id: Optional[int]
    train_number: Optional[str]
    train_name: Optional[str]
    coach: Optional[str]
    berth_no: Optional[int]
    created_at: datetime
    created_by: Optional[str]
    updated_at: datetime
    updated_by: Optional[str]
    rail_sathi_complain_media_files: List[RailSathiComplainMediaResponse]
class TrainResponse(BaseModel):
    train_no: str
    train_name: str
    source: Optional[str]
    destination: Optional[str]
    start_time: Optional[time]
    arrival_time: Optional[time]
class TrainCreateRequest(BaseModel):
    train_no: str
    train_name: str
    source: Optional[str]
    destination: Optional[str]
    start_time: Optional[time]
    arrival_time: Optional[time]
class TrainListResponse(BaseModel):
    message: str
    data: List[TrainResponse]
class SingleTrainResponse(BaseModel):
    message: str
    data: TrainResponse


@app.get("/rs_microservice/complaint/get/{complain_id}", response_model=RailSathiComplainResponse)
async def get_complaint(complain_id: int):
    """Get complaint by ID"""
    try:
        complaint = get_complaint_by_id(complain_id)
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        # Wrap the complaint in the expected response format
        return RailSathiComplainResponse(
            message="Complaint retrieved successfully",
            data=complaint
        )
    except Exception as e:
        logger.error(f"Error getting complaint {complain_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
@app.get("/rs_microservice/trains", response_model=TrainListResponse)
async def get_trains():
    """Get list of all trains"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT train_no, train_name, source, destination, start_time, arrival_time
            FROM trains
        """)
        trains = cursor.fetchall()

        return TrainListResponse(
            message="Train list retrieved successfully",
            data=trains
        )
    except Exception as e:
        logger.error(f"Error fetching train list: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/rs_microservice/train", response_model=SingleTrainResponse)
async def add_train(train: TrainCreateRequest):
    """Add a new train"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO trains (train_no, train_name, source, destination, start_time, arrival_time)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING train_no, train_name, source, destination, start_time, arrival_time
        """, (
            train.train_no,
            train.train_name,
            train.source,
            train.destination,
            train.start_time,
            train.arrival_time
        ))
        new_train = cursor.fetchone()
        connection.commit()

        return SingleTrainResponse(
            message="Train added successfully",
            data=dict(zip(
                ['train_no', 'train_name', 'source', 'destination', 'start_time', 'arrival_time'],
                new_train
            ))
        )

    except Exception as e:
        logger.error(f"Error adding train: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/rs_microservice/trains/{train_no}", response_model=SingleTrainResponse)
async def get_train_by_number(train_no: str):
    """Get a train by its train number"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT train_no, train_name, source, destination, start_time, arrival_time
            FROM trains
            WHERE train_no = %s
        """, (train_no,))
        train = cursor.fetchone()

        if not train:
            raise HTTPException(status_code=404, detail="Train not found")

        return SingleTrainResponse(
            message="Train retrieved successfully",
            data=train
        )

    except Exception as e:
        logger.error(f"Error fetching train {train_no}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/rs_microservice/complaint/get/date/{date_str}", response_model=List[RailSathiComplainResponse])
async def get_complaints_by_date_endpoint(date_str: str, mobile_number: Optional[str] = None):
    """Get complaints by date and mobile number"""
    try:
        # Validate date format
        try:
            complaint_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
        if not mobile_number:
            raise HTTPException(status_code=400, detail="mobile_number parameter is required")
        
        complaints = get_complaints_by_date(complaint_date, mobile_number)
        
        # Wrap each complaint in the expected response format
        response_list = []
        for complaint in complaints:
            response_list.append(RailSathiComplainResponse(
                message="Complaint retrieved successfully",
                data=complaint
            ))
        
        return response_list
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting complaints by date {date_str}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/rs_microservice/complaint/add", response_model=RailSathiComplainResponse)
@app.post("/rs_microservice/complaint/add/", response_model=RailSathiComplainResponse)
async def create_complaint_endpoint_threaded(
    pnr_number: Optional[str] = Form(None),
    is_pnr_validated: Optional[str] = Form("not-attempted"),
    name: Optional[str] = Form(None),
    mobile_number: Optional[str] = Form(None),
    complain_type: Optional[str] = Form(None),
    date_of_journey: Optional[str] = Form(None),
    complain_description: Optional[str] = Form(None),
    complain_date: Optional[str] = Form(None),
    complain_status: str = Form("pending"),
    train_id: Optional[int] = Form(None),
    train_number: Optional[str] = Form(None),
    train_name: Optional[str] = Form(None),
    coach: Optional[str] = Form(None),
    berth_no: Optional[int] = Form(None),
    rail_sathi_complain_media_files: List[UploadFile] = File(default=[])
):
    """Create new complaint with improved file handling"""
    try:
        logger.info(f"Creating complaint for user: {name}")
        logger.info(f"Number of files received: {len(rail_sathi_complain_media_files)}")
        logger.info(f"Request data: {{"
                    f"pnr_number: {pnr_number}, "
                    f"is_pnr_validated: {is_pnr_validated}, "
                    f"name: {name}, "
                    f"mobile_number: {mobile_number}, "
                    f"complain_type: {complain_type}, "
                    f"date_of_journey: {date_of_journey}, "
                    f"complain_description: {complain_description}, "
                    f"complain_date: {complain_date}, "
                    f"complain_status: {complain_status}, "
                    f"train_id: {train_id}, "
                    f"train_number: {train_number}, "
                    f"train_name: {train_name}, "
                    f"coach: {coach}, "
                    f"berth_no: {berth_no}"
                    f"}}")
        
        # Prepare complaint data
        complaint_data = {
            "pnr_number": pnr_number,
            "is_pnr_validated": is_pnr_validated,
            "name": name,
            "mobile_number": mobile_number,
            "complain_type": complain_type,
            "complain_description": complain_description,
            "complain_date": complain_date,
            "date_of_journey": date_of_journey,
            "complain_status": complain_status,
            "train_id": train_id,
            "train_number": train_number,
            "train_name": train_name,
            "coach": coach,
            "berth_no": berth_no,
            "created_by": name
        }
        
        # Create complaint
        complaint = create_complaint(complaint_data)
        complain_id = complaint["complain_id"]
        logger.info(f"Complaint created with ID: {complain_id}")
        
        # Handle file uploads if any files are provided
        if rail_sathi_complain_media_files and len(rail_sathi_complain_media_files) > 0:
            logger.info(f"Processing {len(rail_sathi_complain_media_files)} files")
            
            # Read all file contents first (before threading)
            file_data_list = []
            for file_obj in rail_sathi_complain_media_files:
                if file_obj.filename:  # Check if file is actually uploaded
                    file_content = await file_obj.read()
                    file_data_list.append({
                        'content': file_content,
                        'filename': file_obj.filename,
                        'content_type': file_obj.content_type
                    })
                    logger.info(f"Read file: {file_obj.filename}, size: {len(file_content)}")
            
            # Process files in threads
            threads = []
            for file_data in file_data_list:
                # Create a mock file object for threading
                class MockFile:
                    def __init__(self, content, filename, content_type):
                        self.content = content
                        self.filename = filename
                        self.content_type = content_type
                    
                    def read(self):
                        return self.content
                
                mock_file = MockFile(file_data['content'], file_data['filename'], file_data['content_type'])
                t = threading.Thread(
                    target=upload_file_thread, 
                    args=(mock_file, complain_id, name or ''),
                    name=f"FileUpload-{complain_id}-{file_data['filename']}"
                )
                t.start()
                threads.append(t)
                logger.info(f"Started thread for file: {file_data['filename']}")
            
            # Wait for all threads to complete
            for t in threads:
                t.join()
                logger.info(f"Thread completed: {t.name}")
        
        # Add a small delay to ensure database operations complete
        await asyncio.sleep(1)
        
        # Get updated complaint with media files
        updated_complaint = get_complaint_by_id(complain_id)
        logger.info(f"Final complaint data retrieved with {len(updated_complaint.get('rail_sathi_complain_media_files', []))} media files")
        
        return {
            "message": "Complaint created successfully",
            "data": updated_complaint
        }
        
    except Exception as e:
        logger.error(f"Error creating complaint: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.patch("/rs_microservice/complaint/update/{complain_id}", response_model=RailSathiComplainResponse)
async def update_complaint_endpoint(
    complain_id: int,
    pnr_number: Optional[str] = Form(None),
    is_pnr_validated: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    mobile_number: Optional[str] = Form(None),
    complain_type: Optional[str] = Form(None),
    complain_description: Optional[str] = Form(None),
    complain_date: Optional[str] = Form(None),
    complain_status: Optional[str] = Form(None),
    train_id: Optional[int] = Form(None),
    train_number: Optional[str] = Form(None),
    train_name: Optional[str] = Form(None),
    coach: Optional[str] = Form(None),
    berth_no: Optional[int] = Form(None),
    rail_sathi_complain_media_files: List[UploadFile] = File(default=[])
):
    """Update complaint (partial update)"""
    try:
        logger.info(f"Updating complaint {complain_id} for user: {name}")
        logger.info(f"Number of files received: {len(rail_sathi_complain_media_files)}")
        
        # Check if complaint exists and validate permissions
        existing_complaint = get_complaint_by_id(complain_id)
        if not existing_complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        # # Check permissions
        # if (existing_complaint["created_by"] != name or 
        #     existing_complaint["complain_status"] == "completed" or 
        #     existing_complaint["mobile_number"] != mobile_number):
        #     raise HTTPException(status_code=403, detail="Only user who created the complaint can update it.")
        
        # Prepare update data (only include non-None values)
        update_data = {}
        if pnr_number is not None: update_data["pnr_number"] = pnr_number
        if is_pnr_validated is not None: update_data["is_pnr_validated"] = is_pnr_validated
        if name is not None: update_data["name"] = name
        if mobile_number is not None: update_data["mobile_number"] = mobile_number
        if complain_type is not None: update_data["complain_type"] = complain_type
        if complain_description is not None: update_data["complain_description"] = complain_description
        if complain_date is not None: update_data["complain_date"] = complain_date
        if complain_status is not None: update_data["complain_status"] = complain_status
        if train_id is not None: update_data["train_id"] = train_id
        if train_number is not None: update_data["train_number"] = train_number
        if train_name is not None: update_data["train_name"] = train_name
        if coach is not None: update_data["coach"] = coach
        if berth_no is not None: update_data["berth_no"] = berth_no
        update_data["updated_by"] = name
        
        # Update complaint
        updated_complaint = update_complaint(complain_id, update_data)
        logger.info(f"Complaint {complain_id} updated successfully")
        
        # Handle file uploads if any files are provided (similar to create endpoint)
        if rail_sathi_complain_media_files and len(rail_sathi_complain_media_files) > 0:
            logger.info(f"Processing {len(rail_sathi_complain_media_files)} files")
            
            # Read all file contents first (before threading)
            file_data_list = []
            for file_obj in rail_sathi_complain_media_files:
                if file_obj.filename:  # Check if file is actually uploaded
                    file_content = await file_obj.read()
                    file_data_list.append({
                        'content': file_content,
                        'filename': file_obj.filename,
                        'content_type': file_obj.content_type
                    })
                    logger.info(f"Read file: {file_obj.filename}, size: {len(file_content)}")
            
            # Process files in threads
            threads = []
            for file_data in file_data_list:
                # Create a mock file object for threading
                class MockFile:
                    def __init__(self, content, filename, content_type):
                        self.content = content
                        self.filename = filename
                        self.content_type = content_type
                    
                    def read(self):
                        return self.content
                
                mock_file = MockFile(file_data['content'], file_data['filename'], file_data['content_type'])
                t = threading.Thread(
                    target=upload_file_thread, 
                    args=(mock_file, complain_id, name or ''),
                    name=f"FileUpload-{complain_id}-{file_data['filename']}"
                )
                t.start()
                threads.append(t)
                logger.info(f"Started thread for file: {file_data['filename']}")
            
            # Wait for all threads to complete
            for t in threads:
                t.join()
                logger.info(f"Thread completed: {t.name}")
        
        # Add a small delay to ensure database operations complete
        await asyncio.sleep(1)
        
        # Get final updated complaint with media files
        final_complaint = get_complaint_by_id(complain_id)
        logger.info(f"Final complaint data retrieved with {len(final_complaint.get('rail_sathi_complain_media_files', []))} media files")
        
        return {
            "message": "Complaint updated successfully",
            "data": final_complaint
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating complaint {complain_id}: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.put("/rs_microservice/complaint/update/{complain_id}", response_model=RailSathiComplainResponse)
async def replace_complaint_endpoint(
    complain_id: int,
    pnr_number: Optional[str] = Form(None),
    is_pnr_validated: str = Form("not-attempted"),
    name: Optional[str] = Form(None),
    mobile_number: Optional[str] = Form(None),
    complain_type: Optional[str] = Form(None),
    complain_description: Optional[str] = Form(None),
    complain_date: Optional[str] = Form(None),
    complain_status: str = Form("pending"),
    train_id: Optional[int] = Form(None),
    train_number: Optional[str] = Form(None),
    train_name: Optional[str] = Form(None),
    coach: Optional[str] = Form(None),
    berth_no: Optional[int] = Form(None),
    rail_sathi_complain_media_files: List[UploadFile] = File(default=[])
):
    """Replace complaint (full update)"""
    try:
        logger.info(f"Replacing complaint {complain_id} for user: {name}")
        logger.info(f"Number of files received: {len(rail_sathi_complain_media_files)}")
        
        # Check if complaint exists and validate permissions
        existing_complaint = get_complaint_by_id(complain_id)
        if not existing_complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        # Check permissions
        if (existing_complaint["created_by"] != name or 
            existing_complaint["complain_status"] == "completed" or 
            existing_complaint["mobile_number"] != mobile_number):
            raise HTTPException(status_code=403, detail="Only user who created the complaint can update it.")
        
        # Prepare full update data
        update_data = {
            "pnr_number": pnr_number,
            "is_pnr_validated": is_pnr_validated,
            "name": name,
            "mobile_number": mobile_number,
            "complain_type": complain_type,
            "complain_description": complain_description,
            "complain_date": complain_date,
            "complain_status": complain_status,
            "train_id": train_id,
            "train_number": train_number,
            "train_name": train_name,
            "coach": coach,
            "berth_no": berth_no,
            "updated_by": name
        }
        
        # Update complaint
        updated_complaint = update_complaint(complain_id, update_data)
        logger.info(f"Complaint {complain_id} replaced successfully")
        
        # Handle file uploads if any files are provided
        if rail_sathi_complain_media_files and len(rail_sathi_complain_media_files) > 0:
            logger.info(f"Processing {len(rail_sathi_complain_media_files)} files")
            
            # Read all file contents first (before threading)
            file_data_list = []
            for file_obj in rail_sathi_complain_media_files:
                if file_obj.filename:  # Check if file is actually uploaded
                    file_content = await file_obj.read()
                    file_data_list.append({
                        'content': file_content,
                        'filename': file_obj.filename,
                        'content_type': file_obj.content_type
                    })
                    logger.info(f"Read file: {file_obj.filename}, size: {len(file_content)}")
            
            # Process files in threads
            threads = []
            for file_data in file_data_list:
                # Create a mock file object for threading
                class MockFile:
                    def __init__(self, content, filename, content_type):
                        self.content = content
                        self.filename = filename
                        self.content_type = content_type
                    
                    def read(self):
                        return self.content
                
                mock_file = MockFile(file_data['content'], file_data['filename'], file_data['content_type'])
                t = threading.Thread(
                    target=upload_file_thread, 
                    args=(mock_file, complain_id, name or ''),
                    name=f"FileUpload-{complain_id}-{file_data['filename']}"
                )
                t.start()
                threads.append(t)
                logger.info(f"Started thread for file: {file_data['filename']}")
            
            # Wait for all threads to complete
            for t in threads:
                t.join()
                logger.info(f"Thread completed: {t.name}")
        
        # Add a small delay to ensure database operations complete
        await asyncio.sleep(1)
        
        # Get final updated complaint with media files
        final_complaint = get_complaint_by_id(complain_id)
        logger.info(f"Final complaint data retrieved with {len(final_complaint.get('rail_sathi_complain_media_files', []))} media files")
        
        # Return properly formatted response (this was the missing part!)
        return {
            "message": "Complaint replaced successfully",
            "data": final_complaint
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replacing complaint {complain_id}: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/rs_microservice/complaint/delete/{complain_id}")
async def delete_complaint_endpoint(
    complain_id: int,
    name: str = Form(...),
    mobile_number: str = Form(...)
):
    """Delete complaint"""
    try:
        logger.info(f"Deleting complaint {complain_id} for user: {name}")
        
        # Check if complaint exists and validate permissions
        existing_complaint = get_complaint_by_id(complain_id)
        if not existing_complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        # Check permissions
        if (existing_complaint["created_by"] != name or 
            existing_complaint["complain_status"] == "completed" or 
            existing_complaint["mobile_number"] != mobile_number):
            raise HTTPException(status_code=403, detail="Only user who created the complaint can delete it.")
        
        # Delete complaint
        delete_complaint(complain_id)
        logger.info(f"Complaint {complain_id} deleted successfully")
        
        return {"message": "Complaint deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting complaint {complain_id}: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/rs_microservice/media/delete/{complain_id}")
async def delete_complaint_media_endpoint(
    complain_id: int,
    name: str = Form(...),
    mobile_number: str = Form(...),
    deleted_media_ids: List[int] = Form(...)
):
    """Delete complaint media files"""
    try:
        logger.info(f"Deleting media files for complaint {complain_id} for user: {name}")
        logger.info(f"Media IDs to delete: {deleted_media_ids}")
        
        # Check if complaint exists and validate permissions
        existing_complaint = get_complaint_by_id(complain_id)
        if not existing_complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        # Check permissions
        if (existing_complaint["created_by"] != name or 
            existing_complaint["complain_status"] == "completed" or 
            existing_complaint["mobile_number"] != mobile_number):
            raise HTTPException(status_code=403, detail="Only user who created the complaint can update it.")
        
        if not deleted_media_ids:
            raise HTTPException(status_code=400, detail="No media IDs provided for deletion.")
        
        # Delete media files
        deleted_count = delete_complaint_media(complain_id, deleted_media_ids)
        
        if deleted_count == 0:
            raise HTTPException(status_code=400, detail="No matching media files found for deletion.")
        
        logger.info(f"{deleted_count} media file(s) deleted successfully for complaint {complain_id}")
        
        return {"message": f"{deleted_count} media file(s) deleted successfully."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting complaint media {complain_id}: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    

def make_json_serializable(data):
    if isinstance(data, dict):
        return {k: make_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_json_serializable(i) for i in data]
    elif isinstance(data, (time, date, datetime)):
        return data.isoformat()
    else:
        return data

@app.get("/rs_microservice/train_details/{train_no}")
def get_train_details(train_no: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("SELECT * FROM trains_traindetails WHERE train_no = %s", (train_no,))
        train_detail = cursor.fetchone()

        if not train_detail:
            return JSONResponse(content={"error": "Train not found"}, status_code=404)

        depot_code = train_detail.get('Depot')
        cursor.execute("SELECT * FROM station_Depot WHERE depot_code = %s", (depot_code,))
        depot = cursor.fetchone()

        if depot:
            division_code = depot.get("division_id")
            cursor.execute("SELECT * FROM station_division WHERE division_id = %s", (division_code,))
            division = cursor.fetchone()

            zone_code = None
            if division:
                zone_id = division.get("zone_id")
                cursor.execute("SELECT * FROM station_zone WHERE zone_id = %s", (zone_id,))
                zone = cursor.fetchone()
                zone_code = zone.get("zone_code") if zone else None

            extra_info = {
                "depot_code": depot.get("depot_code"),
                "division_code": division.get("division_code") if division else None,
                "zone_code": zone_code,
            }
        else:
            extra_info = {
                "depot_code": None,
                "division_code": None,
                "zone_code": None,
            }

        train_detail['extra_info'] = extra_info

        # ✅ Convert to JSON-safe format before returning
        safe_train_detail = make_json_serializable(train_detail)
        return JSONResponse(content=safe_train_detail)

    finally:
        cursor.close()
        conn.close()
    
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)