# ExpiryPalNext - Smart Refrigerator Management System

An intelligent shared refrigerator management system that allows multiple users to collaborate on inventory, receive recipe suggestions based on available ingredients, and manage a shared shopping list.

## Description

ExpiryPalNext is a web application that combines artificial intelligence, IoT, and multi-user collaboration to optimize refrigerator management. The system uses automatic object detection, intelligent recipe recommendations, and collaborative inventory management.

## Project Architecture

```
ExpiryPalNext/
├── Frontend/          # React + Vite + Tailwind CSS
├── Backend/           # Flask + MongoDB + Firebase
├── ML/               # YOLO + CLIP + Local Storage
└── docs/             # Project documentation
```

## Installation

### Prerequisites
- Node.js 18+ 
- Python 3.8+
- MongoDB
- Firebase account

### Frontend (React + Vite)

```bash
cd Frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Backend (Flask + MongoDB)

```bash
cd Backend
pip install -r requirements.txt
cp env.example .env
# Configure variables in .env
python app.py
```

The backend will be available at `http://localhost:5000`

### ML Service (YOLO + CLIP)

```bash
cd ML
pip install -r requirements.txt
cp env.example .env
# Configure variables in .env
python app.py
```

The ML service will be available at `http://localhost:5001`

## Configuration

### Environment Variables

1. **Backend (.env)**:
   - `MONGO_URI`: MongoDB connection
   - `SECRET_KEY`: Flask secret key
   - `FIREBASE_*`: Firebase credentials

2. **ML (.env)**:
   - `BE_URL`: Backend API URL
   - `STORAGE_PATH`: Local storage path



## Main Features

- 🔍 **Automatic Detection**: Product recognition through AI
- 👥 **Multi-user Collaboration**: Shared refrigerator management
- 🍳 **Intelligent Recipes**: Suggestions based on available ingredients
- 📱 **Push Notifications**: Real-time expiration alerts
- 🛒 **Shared Shopping List**: Group purchase coordination

## Technologies Used

### Frontend
- React 18.3.1
- Vite
- Tailwind CSS
- Material-UI
- Firebase Authentication
- ZXing (QR Scanner)

### Backend
- Flask 3.0.3
- MongoDB
- Firebase Admin SDK

### Machine Learning
- YOLOv8x (Object Detection)
- CLIP (Feature Extraction)
- OpenCV (Image Processing)
- Scikit-learn (Similarity)


## Development Team

See [Participants.json](./Participants.json) for the complete team list.


