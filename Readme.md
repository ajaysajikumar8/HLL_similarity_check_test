Here are the complete instructions for creating a new virtual environment, installing dependencies from a `requirements.txt` file, and running the Python file:

---

## Setup: 

### Creating a Virtual Environment

1. Open your terminal.

2. Navigate to your project directory.

3. Create a new virtual environment by running the following command:
   ```bash
   python -m venv .venv
   ```

### Activating the Virtual Environment 

4. Activate the virtual environment by running the following command:
   ```bash
   .venv/Scripts/activate
   ```

   Or if running in Ubuntu Server:
   ```bash
   source .venv/bin/activate
   ```

### Installing Dependencies

5. Once the virtual environment is activated, install the required dependencies by running:
   ```bash
   pip install -r requirements.txt
   ```

<br/>

---

<br/>

## Running the Python File

### Activating the Virtual Environment (Skip if already activated)

1. Activate the virtual environment by running the following command:
   ```bash
   .venv/Scripts/activate
   ```

   Or if running in Ubuntu Server:
   ```bash
   source .venv/bin/activate
   ```


2. After activating the virtual environment, Move inside either backend or frontend folder:
   
   ```bash
   ls backend
   ```
   
   Or 

   ```bash
   ls frontend
   ```


7. After Moving inside the folder, run the following command: 
   
   ```bash
   python run.py
   ```

---
