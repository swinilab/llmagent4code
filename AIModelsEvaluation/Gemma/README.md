**IV. Setup Instructions**

1.  **Install Python:** Ensure you have Python 3.6 or higher installed.
2.  **Install Flask and SQLAlchemy:**
    ```bash
    pip install flask flask-sqlalchemy
    ```
3.  **Install React:**

    ```bash
    npx create-react-app frontend
    cd frontend
    npm start
    ```

4.  **Run Backend:** Navigate to the `backend` directory and run the Python script: `python app.py`
5.  **Access Frontend:** Open your web browser and go to `http://localhost:3000` to view the React frontend. The frontend will fetch data from the Flask backend at `http://localhost:5000`.
6.  **Database:** The database `order_management.db` will be created in the backend directory.
