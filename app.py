from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget, ValueTarget
from streaming_form_data.validators import MaxSizeValidator
import streaming_form_data
from starlette.requests import ClientDisconnect
from urllib.parse import unquote
import os
import json
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Configure size limits
MAX_FILE_SIZE = 1024 * 1024 * 1024 * 4  # 4GB
MAX_REQUEST_BODY_SIZE = MAX_FILE_SIZE + 1024  # Allow extra bytes for form data

app = FastAPI()

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")

# Add route to serve the HTML page
@app.get("/")
async def get_upload_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Custom exception for body size validation
class MaxBodySizeException(Exception):
    def __init__(self, body_len: int):
        self.body_len = body_len

# Custom validator for total request body size
class MaxBodySizeValidator:
    def __init__(self, max_size: int):
        self.body_len = 0
        self.max_size = max_size

    def __call__(self, chunk: bytes):
        self.body_len += len(chunk)
        if self.body_len > self.max_size:
            raise MaxBodySizeException(body_len=self.body_len)

@app.post('/upload')
async def upload_file_with_data(request: Request):
    # Initialize body size validator
    body_validator = MaxBodySizeValidator(MAX_REQUEST_BODY_SIZE)
    
    # Get filename from header
    filename = request.headers.get('filename')
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Filename header is missing'
        )
    
    try:
        # Decode filename and create filepath
        filename = unquote(filename)
        filepath = os.path.join(UPLOAD_DIR, os.path.basename(filename))
        
        # Setup file target with size validation
        file_ = FileTarget(filepath, validator=MaxSizeValidator(MAX_FILE_SIZE))
        
       
        # Setup individual form field targets instead of a single data target
        name_field = ValueTarget()
        description_field = ValueTarget()
        
        # Initialize parser
       # Initialize parser
        parser = StreamingFormDataParser(headers=request.headers)
        parser.register('file', file_)
        parser.register('name', name_field)
        parser.register('description', description_field)
        
        
        
        
        # Process the stream
        async for chunk in request.stream():
            body_validator(chunk)  # Validate total body size
            parser.data_received(chunk)
            
    except ClientDisconnect:
        print("Client disconnected during upload")
        # Cleanup partial file if needed
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_499_CLIENT_CLOSED_REQUEST,
            detail="Client disconnected during upload"
        )
    
    except MaxBodySizeException as e:
        # Cleanup partial file if needed
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f'Maximum request body size limit ({MAX_REQUEST_BODY_SIZE} bytes) exceeded ({e.body_len} bytes read)'
        )
    
    except streaming_form_data.validators.ValidationError:
        # Cleanup partial file if needed
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f'Maximum file size limit ({MAX_FILE_SIZE} bytes) exceeded'
        )
    
    except Exception as e:
        # Cleanup partial file if needed
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Upload error: {str(e)}'
        )
    
    # Validate file was received
    if not file_.multipart_filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='File is missing'
        )
    
    
     # Extract individual form fields
    name = name_field.value.decode() if name_field.value else ""
    description = description_field.value.decode() if description_field.value else ""
    
     # Print the form field values
    print(f"Name: {name}")
    print(f"Description: {description}")
    
    # Process metadata if provided
    metadata_content = {
        "name": name,
        "description": description
    }
   
    # File is now fully available on the server
    return {
        "message": f"Successfully uploaded {filename}",
        "filename": filename,
        "file_size": os.path.getsize(filepath),
        "metadata": metadata_content,
        "status": "complete",
        "file_path": filepath
    }

@app.post('/upload-multiple')
async def upload_multiple_files(request: Request):
    try:
        parser = StreamingFormDataParser(headers=request.headers)
        # Setup individual form field targets
        name_field = ValueTarget()
        description_field = ValueTarget()
        
        parser.register('name', name_field)
        parser.register('description', description_field)

        

        # Extract filenames from headers
        headers = dict(request.headers)
        filenames = []
        file_targets = []
        
        # Register all file targets
        i = 0
        while True:
            filename = headers.get(f'filename{i}', None)
            if filename is None:
                break
                
            filename = unquote(filename)
            filenames.append(filename)
            
            filepath = os.path.join(UPLOAD_DIR, os.path.basename(filename))
            file_ = FileTarget(filepath, validator=MaxSizeValidator(MAX_FILE_SIZE))
            file_targets.append((filepath, file_))
            
            parser.register(f'file{i}', file_)
            i += 1

        # Process the stream
        async for chunk in request.stream():
            parser.data_received(chunk)
            
    except ClientDisconnect:
        print("Client disconnected during upload")
        # Cleanup partial files
        for filepath, _ in file_targets:
            if os.path.exists(filepath):
                os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_499_CLIENT_CLOSED_REQUEST,
            detail="Client disconnected during upload"
        )
    
    except streaming_form_data.validators.ValidationError:
        # Cleanup partial files
        for filepath, _ in file_targets:
            if os.path.exists(filepath):
                os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f'Maximum file size limit ({MAX_FILE_SIZE} bytes) exceeded'
        )
    
    except Exception as e:
        # Cleanup partial files
        for filepath, _ in file_targets:
            if os.path.exists(filepath):
                os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Upload error: {str(e)}'
        )

    # Extract individual form fields
    name = name_field.value.decode() if name_field.value else ""
    description = description_field.value.decode() if description_field.value else ""
    # Process metadata if provided
    metadata_content = {
        "name": name,
        "description": description
    }
    
    
    # All files are now fully available on the server
    uploaded_files = []
    for filepath, file_ in file_targets:
        if file_.multipart_filename and os.path.exists(filepath):
            uploaded_files.append({
                "filename": file_.multipart_filename,
                "file_size": os.path.getsize(filepath),
                "file_path": filepath
            })
    
    return {
        "message": f"Successfully uploaded {len(uploaded_files)} files",
        "files": uploaded_files,
        "metadata": metadata_content,
        "status": "complete"
    }