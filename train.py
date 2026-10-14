import face_recognition
import pickle
import cv2
import os
import glob

print("[INFO] quantifying faces and building encodings...")

# Get all image paths from dataset folder using glob (No imutils required)
imagePaths = []
for ext in ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG"):
    imagePaths.extend(glob.glob(os.path.join("dataset", ext)))

# Check if dataset folder is empty
if len(imagePaths) == 0:
    print("[ERROR] No images found in 'dataset' folder! Please register a student first.")
    exit()

knownEncodings = []
knownNames = []

for (i, imagePath) in enumerate(imagePaths):
    print(f"[INFO] Processing image {i + 1}/{len(imagePaths)}: {imagePath}")
    
    # Extract filename: e.g., "Farjuk_CSE001_0.jpg" -> "Farjuk_CSE001"
    filename = os.path.basename(imagePath)
    name_parts = filename.split(".")[0].split("_")
    
    if len(name_parts) >= 2:
        student_identifier = f"{name_parts[0]}_{name_parts[1]}"
    else:
        student_identifier = name_parts[0]

    # Load image and convert from BGR (OpenCV) to RGB (face_recognition)
    image = cv2.imread(imagePath)
    if image is None:
        continue
        
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Detect face bounding boxes
    boxes = face_recognition.face_locations(rgb, model="hog")

    # Compute facial embeddings
    encodings = face_recognition.face_encodings(rgb, boxes)

    for encoding in encodings:
        knownEncodings.append(encoding)
        knownNames.append(student_identifier)

print("[INFO] Serializing encodings to pickle file...")
os.makedirs("embeddings", exist_ok=True)
data = {"encodings": knownEncodings, "names": knownNames}

with open("embeddings/encodings.pickle", "wb") as f:
    f.write(pickle.dumps(data))

print("[INFO] Training completed successfully! Encodings saved in 'embeddings/encodings.pickle'.")