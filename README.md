# Fitness Studio Booking API

A RESTful API for managing fitness class bookings built with FastAPI and SQLite.

## Features

- Create and manage fitness classes
- View upcoming fitness classes with timezone support
- Book a spot in a class with automatic slot management
- View all bookings by email
- Timezone-aware scheduling (Asia/Kolkata by default)
- Input validation and error handling
- API documentation with Swagger UI
- Thread-safe booking with database-level locking

## Timezone Handling

All datetime values are stored in UTC in the database. The API accepts and returns times in the specified timezone (Asia/Kolkata by default).

### Key Points:
- All class times are stored in UTC in the database
- The API accepts times in any valid timezone (default: Asia/Kolkata)
- Responses include times in the requested timezone
- The `timezone` parameter is available on all relevant endpoints
- Timezone validation ensures only valid timezones are accepted

### Example Workflow:

1. **Create a class in IST (Asia/Kolkata):**
   ```
   POST /classes?timezone=Asia/Kolkata
   {
     "start_time": "2025-08-19T07:00:00+05:30",
     "end_time": "2025-08-19T08:00:00+05:30",
     ...
   }
   ```

2. **View the same class in a different timezone:**
   ```
   GET /classes?timezone=America/New_York
   ```
   The response will show the class times converted to New York time.

3. **Bookings maintain the original timezone of the class** but can be viewed in any timezone.

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd omnify
   ```

2. **Create and activate a virtual environment**
   ```bash
   # On macOS/Linux
   python -m venv venv
   source venv/bin/activate
   
   # On Windows
   # python -m venv venv
   # .\venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   python init_db.py
   ```
   This will create a SQLite database with some sample fitness classes.

## Running the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

## API Documentation

Once the server is running, you can access:

- Interactive API documentation: `http://127.0.0.1:8000/api/v1/docs`
- OpenAPI schema: `http://127.0.0.1:8000/api/v1/openapi.json`

## API Endpoints

### `POST /classes`

Create a new fitness class.

**Query Parameters:**
- `timezone`: Timezone for the class times (default: Asia/Kolkata)

**Request Body:**
```json
{
  "name": "Morning Yoga",
  "description": "Energizing morning yoga session",
  "instructor": "Priya Sharma",
  "start_time": "2025-08-19T07:00:00+05:30",
  "end_time": "2025-08-19T08:00:00+05:30",
  "capacity": 15
}
```

### `GET /classes`

List all upcoming fitness classes.

**Query Parameters:**
- `timezone`: Timezone for displaying class times (default: Asia/Kolkata)
- `skip`: Number of records to skip (pagination)
- `limit`: Maximum number of records to return (max 1000)

### `POST /book`

Book a spot in a fitness class.

**Query Parameters:**
- `timezone`: Timezone for the response times (default: Asia/Kolkata)

**Request Body:**
```json
{
  "fitness_class_id": 1,
  "client_name": "John Doe",
  "client_email": "john@example.com"
}
```

### `GET /bookings`

List all bookings for a specific email address.

**Query Parameters:**
- `email`: Email address to look up bookings for (required)
- `timezone`: Timezone for displaying booking times (default: Asia/Kolkata)
- `upcoming`: If true, only return upcoming bookings (default: true)
- `skip`: Number of records to skip (pagination)
- `limit`: Maximum number of records to return (max 1000)

## Running Tests

```bash
pytest
```

## Project Structure

```
omnify/
├── app/
│   ├── api/               # API routes
│   ├── core/              # Core functionality
│   ├── db/                # Database configuration
│   ├── models/            # Database models
│   ├── schemas/           # Pydantic schemas
│   └── main.py            # FastAPI application
├── tests/                 # Test files
├── init_db.py             # Database initialization
├── requirements.txt        # Project dependencies
└── README.md              # This file
```

## License

MIT
