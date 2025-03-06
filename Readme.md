## Troubleshooting

### Empty Form Fields

If form fields appear empty in the backend:

1. **Check field names**: Ensure field names match exactly between frontend and backend
2. **Print request headers**: Debug by printing `request.headers` to see what's coming in
3. **Check form field registration**: Verify all fields are properly registered with the parser
4. **Test with small files**: File size can impact how browsers handle multipart/form-data
5. **Check for encoding issues**: Ensure proper encoding/decoding of form fields

### Network Tab Shows "No payload"

When using browser DevTools, you might see "No payload for this request" in the Network tab, even though the upload works correctly:

1. **This is normal**: Browser DevTools sometimes doesn't display multipart/form-data requests with large files
2. **Workaround**: Use smaller test files to see the payload in DevTools
3. **Alternative debugging**: Log FormData entries in JavaScript before sending
4. **Server-side debugging**: Print received form fields in the backend code

### File Size Limitations

When dealing with large files:

1. **Browser limitations**: Some browsers may have memory restrictions on file uploads
2. **Server configuration**: Check server timeout and size limit settings
3. **Validation settings**: Adjust `MAX_FILE_SIZE` and `MAX_REQUEST_BODY_SIZE` as needed
4. **Proxy settings**: If using a proxy (like Nginx), check its client_max_body_size setting

### Other Common Issues

1. **CORS errors**: Ensure CORS is properly configured if frontend and backend are on different domains
2. **Network timeouts**: For very large files, increase timeout settings
3. **Missing headers**: Ensure required headers (like filename) are being sent
4. **Memory usage**: Monitor server memory during large uploads
5. **Disk space**: Ensure sufficient disk space for uploaded files# Streaming File Upload System Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [How File Streaming Works](#how-file-streaming-works)
6. [Size Validation](#size-validation)
7. [Error Handling](#error-handling)
8. [API Endpoints](#api-endpoints)
9. [Form Data Handling](#form-data-handling)
10. [Function Reference](#function-reference)
11. [Project Structure](#project-structure)
12. [Installation & Setup](#installation--setup)
13. [Handling Multiple Files](#handling-multiple-files)
14. [Example Usage](#example-usage)
15. [Customization Options](#customization-options)
16. [Troubleshooting](#troubleshooting)

## Introduction

This system implements a high-performance, memory-efficient approach to uploading large files from the frontend to a FastAPI backend. Unlike traditional file upload methods that load entire files into memory, this system processes file uploads in chunks as they arrive, enabling it to handle very large files efficiently.

The implementation follows the "streaming-form-data" approach, where files are processed and written to disk in real-time as chunks arrive, rather than waiting for the complete file to be uploaded before processing.

## System Architecture

The system consists of two main components:

1. **Backend (FastAPI)**: Receives and processes file uploads using streaming
2. **Frontend (HTML/JavaScript)**: Sends files and metadata to the backend with progress monitoring

The data flow is as follows:

1. User selects file(s) and adds metadata in the browser
2. Frontend sends file(s) and metadata as multipart/form-data
3. Backend receives and processes the data chunks as they arrive
4. Backend saves files to disk and extracts metadata
5. Backend returns confirmation once all files are completely processed

## Backend Implementation

The backend is built using FastAPI and the streaming-form-data library. This combination allows for efficient handling of file uploads with minimal memory usage.

### Key Components

- `StreamingFormDataParser`: Parses incoming multipart/form-data in chunks
- `FileTarget`: Streams file chunks directly to disk as they arrive
- `ValueTarget`: Captures form fields (name, description, etc.)
- Custom size validators: Enforce file size and request body size limits
- Jinja2Templates: Serves the HTML interface
- StaticFiles: Serves static JavaScript files

## Frontend Implementation

The frontend uses standard HTML forms with JavaScript for handling the uploads, monitoring progress, and managing the user interface.

### Key Components

- `XMLHttpRequest`: Used for tracking upload progress
- `FormData`: Used to bundle files and metadata
- Custom progress-tracking functions
- Abort functionality for canceling uploads

## How File Streaming Works

### Step-by-Step Flow

1. **Client-side Preparation**:

   - User selects file(s) and enters name, description in the form
   - Files and individual form fields are bundled into a FormData object
   - Filenames are encoded and added as HTTP headers
   - Upload starts using XMLHttpRequest (for progress tracking) or fetch API

2. **Server-side Processing**:

   - FastAPI receives the request and begins streaming it
   - `StreamingFormDataParser` initializes with request headers
   - `FileTarget` instances are registered for files
   - `ValueTarget` instances are registered for form fields (name, description)
   - As chunks arrive, they are processed by the parser
   - File chunks are written directly to disk
   - Form field values are captured in memory
   - Size validation happens during streaming

3. **Completion and Response**:
   - Once all chunks are processed, the server confirms files are available
   - Form field values are decoded and printed
   - Response is sent back with file information, form data values, and status

### Memory Efficiency

The key advantage of this approach is memory efficiency. Rather than loading the entire file into memory:

- Files are processed in small chunks (typically a few KB each)
- Each chunk is immediately written to disk and cleared from memory
- This allows handling of very large files (multiple GB) without memory issues
- Only small form field values are kept in memory

## Size Validation

The system implements two levels of size validation:

### 1. File Size Validation

Each file is validated against a maximum size limit using the `MaxSizeValidator`:

```python
file_ = FileTarget(filepath, validator=MaxSizeValidator(MAX_FILE_SIZE))
```

If a file exceeds the limit, an exception is thrown and the upload is rejected before the file is completely transferred.

### 2. Total Request Body Validation

The total request body size is validated to prevent DoS attacks, using a custom validator:

```python
class MaxBodySizeValidator:
    def __init__(self, max_size: int):
        self.body_len = 0
        self.max_size = max_size

    def __call__(self, chunk: bytes):
        self.body_len += len(chunk)
        if self.body_len > self.max_size:
            raise MaxBodySizeException(body_len=self.body_len)
```

## Error Handling

The system implements comprehensive error handling to manage various failure scenarios:

1. **Client Disconnect**:

   - Detects when a client disconnects during upload
   - Cleans up partial files
   - Returns appropriate status code (499)

2. **Size Limit Exceeded**:

   - Detects when file or request body size limits are exceeded
   - Stops processing immediately
   - Cleans up partial files
   - Returns 413 status code with detailed message

3. **General Errors**:
   - Catches any other exceptions during processing
   - Ensures cleanup of partial files
   - Returns 500 status code with detailed message

## API Endpoints

### 1. Single File Upload

```
POST /upload
```

**Purpose**: Upload a single file with associated metadata

**Headers**:

- `filename`: URL-encoded name of the file being uploaded

**Form Fields**:

- `file`: The file content
- `data`: JSON string containing metadata

**Response**: JSON object with file information, metadata, and status

### 2. Multiple Files Upload

```
POST /upload-multiple
```

**Purpose**: Upload multiple files with associated metadata

**Headers**:

- `filename0`, `filename1`, etc.: URL-encoded names of files being uploaded

**Form Fields**:

- `file0`, `file1`, etc.: The file contents
- `data`: JSON string containing metadata

**Response**: JSON object with files information, metadata, and status

## Function Reference

### Backend Functions

#### `MaxBodySizeValidator.__call__(chunk)`

- **Purpose**: Validates the total size of the request body
- **Parameters**: `chunk` - A bytes object containing a portion of the request body
- **Behavior**: Accumulates the size of chunks and raises an exception if the size exceeds the limit
- **Throws**: `MaxBodySizeException` if size exceeds limit

#### `upload_file_with_data(request)`

- **Purpose**: Handles single file upload with metadata
- **Parameters**: `request` - The FastAPI Request object
- **Behavior**:
  1. Validates the filename header
  2. Creates targets for file and metadata
  3. Processes the request stream chunk by chunk
  4. Handles errors and cleanup
  5. Returns response with file info and status
- **Returns**: JSON response with file information and status

#### `upload_multiple_files(request)`

- **Purpose**: Handles multiple file uploads with metadata
- **Parameters**: `request` - The FastAPI Request object
- **Behavior**:
  1. Extracts filenames from headers
  2. Creates targets for each file and metadata
  3. Processes the request stream chunk by chunk
  4. Handles errors and cleanup
  5. Returns response with files info and status
- **Returns**: JSON response with files information and status

### Frontend Functions

#### `uploadFileWithMetadata(file, metadata)`

- **Purpose**: Uploads a single file with metadata using fetch API
- **Parameters**:
  - `file`: File object to upload
  - `metadata`: JavaScript object containing form data (name, description, etc.)
- **Behavior**:
  1. Creates a FormData object
  2. Appends file and individual form fields
  3. Sets appropriate headers including filename
  4. Sends the request using fetch API
  5. Returns Promise resolving to server response
- **Returns**: Promise resolving to server response

#### `uploadMultipleFilesWithMetadata(files, metadata)`

- **Purpose**: Uploads multiple files with metadata using fetch API
- **Parameters**:
  - `files`: Array of File objects to upload
  - `metadata`: JavaScript object containing form data (name, description, etc.)
- **Behavior**:
  1. Creates a FormData object
  2. Appends individual form fields
  3. Sets appropriate headers for each file
  4. Sends the request using fetch API
  5. Returns Promise resolving to server response
- **Returns**: Promise resolving to server response

#### `uploadWithProgress(file, metadata, onProgress)`

- **Purpose**: Uploads a single file with progress tracking using XMLHttpRequest
- **Parameters**:
  - `file`: File object to upload
  - `metadata`: JavaScript object containing form data (name, description, etc.)
  - `onProgress`: Callback function for progress updates
- **Behavior**:
  1. Creates a FormData object
  2. Appends file and metadata fields
  3. Sets up progress event listeners
  4. Sends the request using XMLHttpRequest
  5. Updates progress during upload
- **Returns**: Promise resolving to server response

#### `uploadMultipleWithProgress(files, metadata, onProgress)`

- **Purpose**: Uploads multiple files with progress tracking using XMLHttpRequest
- **Parameters**:
  - `files`: Array of File objects to upload
  - `metadata`: JavaScript object containing form data (name, description, etc.)
  - `onProgress`: Callback function for progress updates
- **Returns**: Promise resolving to server response

## Project Structure

```
large_file_upload/
├── app.py              # FastAPI application
├── templates/          # HTML templates
│   └── index.html      # Upload interface
├── static/             # Static files
│   └── upload.js       # JavaScript for file uploads
├── uploads/            # Directory for uploaded files
└── venv/               # Python virtual environment
```

## Installation & Setup

### Prerequisites

- Python 3.7+
- Node.js and npm (optional, for frontend development)

### Backend Setup

1. Create a virtual environment:

   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:

   ```bash
   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install fastapi uvicorn streaming-form-data python-multipart jinja2
   ```

4. Create necessary directories:

   ```bash
   mkdir uploads templates
   ```

5. Run the application:
   ```bash
   uvicorn app:app --reload
   ```

## Handling Multiple Files

The system supports uploading multiple files in a single request. Here's how it works:

1. **Frontend Preparation**:

   - Each file is added to the FormData with a unique key (`file0`, `file1`, etc.)
   - Corresponding filenames are added as headers (`filename0`, `filename1`, etc.)

2. **Backend Processing**:

   - Backend extracts filenames from headers
   - Each file gets its own `FileTarget` for streaming to disk
   - All files are processed from the same request stream

3. **Error Handling**:
   - If any file fails, all partially uploaded files are cleaned up
   - Error response includes details on which file caused the issue

## Example Usage

### Backend Code (app.py)

```python
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget, ValueTarget
from streaming_form_data.validators import MaxSizeValidator
import streaming_form_data
from starlette.requests import ClientDisconnect
from urllib.parse import unquote
import os
import json

# Configure size limits
MAX_FILE_SIZE = 1024 * 1024 * 1024 * 4  # 4GB
MAX_REQUEST_BODY_SIZE = MAX_FILE_SIZE + 1024  # Allow extra bytes for form data

app = FastAPI()

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
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

        # Setup individual form field targets
        name_field = ValueTarget()
        description_field = ValueTarget()

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

    # Create metadata content from individual fields
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

    # Print the form field values
    print(f"Name: {name}")
    print(f"Description: {description}")

    # Create metadata content from individual fields
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
```

## Form Data Handling

The system supports sending and receiving form data along with file uploads. This is implemented using separate form fields rather than bundling all metadata in a single JSON field.

### Backend Form Data Handling

In the backend, individual form fields are processed using separate `ValueTarget` instances:

```python
# Setup individual form field targets
name_field = ValueTarget()
description_field = ValueTarget()

# Initialize parser
parser = StreamingFormDataParser(headers=request.headers)
parser.register('file', file_)
parser.register('name', name_field)
parser.register('description', description_field)
```

After processing the request stream, the form field values are extracted:

```python
# Extract individual form fields
name = name_field.value.decode() if name_field.value else ""
description = description_field.value.decode() if description_field.value else ""

# Print the form field values
print(f"Name: {name}")
print(f"Description: {description}")

# Create metadata content from individual fields
metadata_content = {
    "name": name,
```
