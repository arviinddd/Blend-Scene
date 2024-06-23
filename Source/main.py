from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
import numpy as np
import cv2
from PIL import Image
import io
import base64
from typing import List

app = FastAPI()

def load_and_align_images(image_paths):
    sift = cv2.SIFT_create()
    base_image = cv2.imread(image_paths[0], cv2.IMREAD_COLOR)
    height, width, channels = base_image.shape
    kp1, des1 = sift.detectAndCompute(cv2.cvtColor(base_image, cv2.COLOR_BGR2GRAY), None)

    for path in image_paths[1:]:
        next_image = cv2.imread(path, cv2.IMREAD_COLOR)
        kp2, des2 = sift.detectAndCompute(cv2.cvtColor(next_image, cv2.COLOR_BGR2GRAY), None)

        flann = cv2.FlannBasedMatcher({'algorithm': 1, 'trees': 5}, {'checks': 50})
        matches = flann.knnMatch(des1, des2, k=2)
        good_matches = [m for m, n in matches if m.distance < 0.7 * n.distance]

        if len(good_matches) > 10:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

            h, status = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
            aligned_image = cv2.warpPerspective(next_image, h, (width, height))
            base_image = aligned_image  
            kp1, des1 = kp2, des2  

    return cv2.cvtColor(base_image, cv2.COLOR_BGR2RGB)

@app.post("/process-images/")
async def process_images(files: List[UploadFile] = File(...)):
    image_paths = []
    for file in files:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        image_path = f"temp_{file.filename}"
        image.save(image_path)
        image_paths.append(image_path)
    
    result_image = load_and_align_images(image_paths)
    result_pil = Image.fromarray(result_image)
    img_bytes = io.BytesIO()
    result_pil.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    
    encoded_img = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    return {"image": encoded_img}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
<html>
<head>
    <title>Upload and Display Image</title>
    <style>
        body {
            background-color: #f4f4f9;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            text-align: center;
            background: white;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }
        h1 {
            color: #333;
        }
        img {
            max-width: 100%;
            margin-top: 20px;
        }
        form {
            margin: 20px 0;
        }
        input[type="file"], input[type="submit"] {
            margin: 10px 0;
        }
        input[type="submit"] {
            background-color: #007BFF;
            border: none;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
        }
        input[type="submit"]:hover {
            background-color: #0056b3;
        }
        /* Modal styles */
        .modal {
            display: none; /* Hidden by default */
            position: fixed; /* Stay in place */
            z-index: 1; /* Sit on top */
            left: 0;
            top: 0;
            width: 100%; /* Full width */
            height: 100%; /* Full height */
            overflow: auto; /* Enable scroll if needed */
            background-color: rgb(0,0,0); /* Fallback color */
            background-color: rgba(0,0,0,0.4); /* Black w/ opacity */
            padding-top: 60px;
        }
        .modal-content {
            background-color: #fefefe;
            margin: 5% auto; /* 15% from the top and centered */
            padding: 20px;
            border: 1px solid #888;
            width: 80%; /* Could be more or less, depending on screen size */
            border-radius: 8px;
        }
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
        }
        .close:hover,
        .close:focus {
            color: black;
            text-decoration: none;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Image Upload</h1>
        <form action="/process-images/" method="post" enctype="multipart/form-data" id="uploadForm">
            <input type="file" name="files" multiple>
            <input type="submit">
        </form>
        <!-- The Modal -->
        <div id="myModal" class="modal">
            <div class="modal-content">
                <span class="close">&times;</span>
                <img id="outputImage" src="" alt="Processed Image will appear here">
            </div>
        </div>
    </div>
    <script>
        const form = document.getElementById('uploadForm');
        const modal = document.getElementById('myModal');
        const span = document.getElementsByClassName("close")[0];

        form.addEventListener('submit', function (event) {
            event.preventDefault();
            const formData = new FormData(form);
            fetch('/process-images/', {
                method: 'POST',
                body: formData,
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('outputImage').src = 'data:image/jpeg;base64,' + data.image;
                modal.style.display = "block";
            })
            .catch(error => console.error('Error:', error));
        });

        span.onclick = function() {
            modal.style.display = "none";
        }

        window.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = "none";
            }
        }
    </script>
</body>
</html>


    """
