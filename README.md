# Real-Time Chat Application

A feature-rich, real-time chat application built with Flask and Socket.IO that enables users to communicate with each other through private and group messages.

##  Features

- **User Authentication**
  - Secure user registration and login system
  - Password hashing for enhanced security
  - Session management with timeout

- **Real-time Messaging**
  - Instant message delivery
  - Online/offline user status
  - Typing indicators
  - Message read receipts
  - Message deletion

- **User Interface**
  - Clean and responsive design
  - User-friendly interface
  - Real-time updates

- **Security**
  - Secure password storage using hashing
  - Session management
  - Input validation

##  Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.7 or higher
- MySQL Server
- pip (Python package manager)

##  Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/being-souL1230/Chat-App.git
   cd Chat-App
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**
   - Create a MySQL database named `chatapp`
   - Update the database configuration in `app.py` with your MySQL credentials:
     ```python
     db_config = {
         'host': 'localhost',
         'user': 'your_username',
         'password': 'your_password',
         'database': 'chatapp'
     }
     ```

5. **Database schema**
   The application will automatically create the required tables on first run.

##  Running the Application

1. **Start the server**
   ```bash
   python app.py
   ```

2. **Access the application**
   Open your web browser and navigate to: `http://localhost:5000`

##  Configuration

You can customize the following settings in `app.py`:

- `SECRET_KEY`: Change this to a secure random key in production
- `PERMANENT_SESSION_LIFETIME`: Session timeout duration (in seconds)
- Database connection settings

##  Project Structure

```
chat_app/
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
└── templates/         # HTML templates
    ├── chat.html      # Main chat interface
    ├── login.html     # Login page
    └── register.html  # Registration page
```

##  Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

##  License

This project is licensed under the MIT License.

##  Acknowledgments

- Built with Flask and Socket.IO
- Uses MySQL for data storage
- Frontend powered by HTML, CSS, and JavaScript

##  Contact

For any queries or support, please contact [rishabdixit402@gmail.com]
