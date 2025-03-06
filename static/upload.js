// Function to upload a single file with metadata
async function uploadFileWithMetadata(file, metadata) {
  try {
    // Create form data
    const formData = new FormData();

    // In uploadFileWithMetadata function
    console.log("Form data being sent - Name:", metadata.name);
    console.log("Form data being sent - Description:", metadata.description);

    // Right before the fetch call
    console.log("FormData contents:");
    for (let pair of formData.entries()) {
      console.log(pair[0] + ": " + pair[1]);
    }

    formData.append("file", file);

    // Add metadata as JSON string
    formData.append("data", JSON.stringify(metadata));
    formData.append("name", metadata.name);
    formData.append("description", metadata.description);

    // Set up headers with filename
    const headers = new Headers();
    headers.append("filename", encodeURIComponent(file.name));

    // Display progress (optional)
    const uploadProgress = document.getElementById("uploadProgress");
    if (uploadProgress) {
      uploadProgress.style.display = "block";
      uploadProgress.value = 0;
    }

    // Send the request
    const response = await fetch("http://localhost:8000/upload", {
      method: "POST",
      headers: headers,
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Upload failed");
    }

    return await response.json();
  } catch (error) {
    console.error("Error uploading file:", error);
    throw error;
  }
}

// Function to upload multiple files with metadata
async function uploadMultipleFilesWithMetadata(files, metadata) {
  try {
    // Create form data
    const formData = new FormData();

    // Add metadata as JSON string
    formData.append("data", JSON.stringify(metadata));
    // Add individual form fields
    formData.append("name", metadata.name);
    formData.append("description", metadata.description);

    // Set up headers
    const headers = new Headers();

    // Add each file to form data and set headers
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      headers.append(`filename${i}`, encodeURIComponent(file.name));
      formData.append(`file${i}`, file);
    }

    // Send the request
    const response = await fetch("http://localhost:8000/upload-multiple", {
      method: "POST",
      headers: headers,
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Upload failed");
    }

    return await response.json();
  } catch (error) {
    console.error("Error uploading files:", error);
    throw error;
  }
}

// Example usage with HTML form
document.addEventListener("DOMContentLoaded", () => {
  const uploadForm = document.getElementById("uploadForm");

  if (uploadForm) {
    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const fileInput = document.getElementById("fileInput");
      const nameInput = document.getElementById("nameInput");
      const descriptionInput = document.getElementById("descriptionInput");
      const resultDiv = document.getElementById("resultDiv");

      if (!fileInput.files || fileInput.files.length === 0) {
        resultDiv.textContent = "Please select a file";
        return;
      }

      try {
        // Create metadata
        const metadata = {
          name: nameInput.value,
          description: descriptionInput.value,
          timestamp: new Date().toISOString(),
        };

        let result;

        // Choose upload function based on selection mode
        const multipleMode = document.getElementById(
          "multipleFilesCheckbox"
        )?.checked;

        if (multipleMode) {
          result = await uploadMultipleFilesWithMetadata(
            fileInput.files,
            metadata
          );
        } else {
          result = await uploadFileWithMetadata(fileInput.files[0], metadata);
        }

        // Display result
        resultDiv.textContent = JSON.stringify(result, null, 2);
      } catch (error) {
        resultDiv.textContent = `Error: ${error.message}`;
      }
    });
  }
});

// Function for monitoring upload progress (can be implemented with XHR)
function uploadWithProgress(file, metadata, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();

    // Add file and metadata
    formData.append("file", file);
    formData.append("data", JSON.stringify(metadata));

    // Setup progress handling
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        const percentComplete = (event.loaded / event.total) * 100;
        if (onProgress) onProgress(percentComplete);
      }
    });

    // Setup completion handler
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response);
        } catch (error) {
          reject(new Error("Invalid response format"));
        }
      } else {
        try {
          const errorData = JSON.parse(xhr.responseText);
          reject(new Error(errorData.detail || `HTTP error ${xhr.status}`));
        } catch (e) {
          reject(new Error(`HTTP error ${xhr.status}`));
        }
      }
    });

    // Setup error handler
    xhr.addEventListener("error", () => {
      reject(new Error("Network error occurred"));
    });

    // Setup abort handler
    xhr.addEventListener("abort", () => {
      reject(new Error("Upload aborted"));
    });

    // Open connection and set headers
    xhr.open("POST", "http://localhost:8000/upload");
    xhr.setRequestHeader("filename", encodeURIComponent(file.name));

    // Send the form data
    xhr.send(formData);
  });
}
