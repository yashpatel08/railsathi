# 🚆 RailSathi Microservices Backend

This is the backend service for the **RailSathi** microservices-based project, built using **Django** and containerized with **Docker** and **Docker Compose**. It includes API routes for managing train data and automates database migration on startup.

---

## 📦 Features

- ✅ Dockerized backend setup with Django  
- ✅ Automatic database migration on container startup  
- ✅ 3 core API routes to interact with train data  
- ✅ `wait-for-it.sh` script ensures the database is ready before Django starts  
- ✅ Modular and extensible structure for future microservices  

---

## 🚀 Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/rs_microservices_be.git
cd rs_microservices_be
```

### 2. Start the application with Docker Compose

```bash
docker-compose up
```

> This command:
> - Waits for the database to be ready using `wait-for-it.sh`
> - Runs migrations automatically
> - Starts the Django development server

---

## 📡 API Endpoints

### 🔹 Get All Trains

- **Method:** `GET`  
- **URL:** `http://localhost:8000/trains/`  
- **Description:** Fetches all train entries from the database.

---

### 🔹 Get Train by ID

- **Method:** `GET`  
- **URL:** `http://localhost:8000/train/<id>`  
- **Description:** Fetches a train entry by its ID.

---

### 🔹 Add a Train

- **Method:** `POST`  
- **URL:** `http://localhost:8000/trains`  
- **Payload:**

```json
{
  "name": "Train Name",
  "source": "Source Station",
  "destination": "Destination Station",
  "departure_time": "HH:MM:SS"
}
```

- **Description:** Adds a new train to the database.

---

## ⚙️ Project Structure

```
.
├── docker-compose.yml
├── Dockerfile
├── wait-for-it.sh
├── manage.py
├── railsathi/            # Django project root
│   └── ...
```

---

## 📝 License

This project is licensed under the MIT License.

---

## 🙌 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

---

## 👨‍💻 Author

**Yash Patel**  [@yashpatel](https://github.com/yashpatel08)
