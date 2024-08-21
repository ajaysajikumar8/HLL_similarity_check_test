### **API Documentation (Python Similarity Check)**



---

### **1. Match Compositions**
- **Endpoint:** `/match-compositions`
- **Method:** `POST`
- **Description:** Upload an Excel file and perform fuzzy matching of compositions.
- **Request:**
  - **Content-Type:** `multipart/form-data`
  - **Parameters:**
    - `file`: The Excel file containing compositions to match.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object containing matched and unmatched compositions.
  - **Error:**
    - **Status:** `400 Bad Request` or `500 Internal Server Error`
    - **Body:** JSON object with an error message.

---

### **2. Get All Compositions**
- **Endpoint:** `/get-all-compositions`
- **Method:** `GET`
- **Description:** Retrieve all compositions from the database.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object containing a list of all compositions.
  - **Error:**
    - **Status:** `500 Internal Server Error`
    - **Body:** JSON object with an error message.

---

### **3. Add New Composition**
- **Endpoint:** `/add-new-composition`
- **Method:** `POST`
- **Description:** Add a new composition as an approver.
- **Request:**
  - **Content-Type:** `application/x-www-form-urlencoded`
  - **Parameters:**
    - `content_code` (optional): Code associated with the content.
    - `composition_name` (required): Name of the composition.
    - `dosage_form` (optional): Form in which the composition is administered.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with a success message.
  - **Error:**
    - **Status:** `400 Bad Request` or `500 Internal Server Error`
    - **Body:** JSON object with an error message.

---

### **4. Get Composition by ID**
- **Endpoint:** `/get-composition/<int:composition_id>`
- **Method:** `GET`
- **Description:** Fetch details of a composition by its ID.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with composition details.
  - **Error:**
    - **Status:** `404 Not Found` or `500 Internal Server Error`
    - **Body:** JSON object with an error message.

---

### **5. Update Composition**
- **Endpoint:** `/update-composition/<int:composition_id>`
- **Method:** `PUT`
- **Description:** Update details of an existing composition.
- **Request:**
  - **Content-Type:** `application/x-www-form-urlencoded`
  - **Parameters:**
    - `content_code` (optional): Code associated with the content.
    - `composition_name` (optional): Name of the composition.
    - `dosage_form` (optional): Form in which the composition is administered.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with a success message.
  - **Error:**
    - **Status:** `400 Bad Request` or `500 Internal Server Error`
    - **Body:** JSON object with an error message.

---

### **6. Delete Composition**
- **Endpoint:** `/delete-composition/<int:composition_id>`
- **Method:** `DELETE`
- **Description:** Delete a composition by its ID.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with a success message.
  - **Error:**
    - **Status:** `500 Internal Server Error`
    - **Body:** JSON object with an error message.

---

### **7. Request Composition**
- **Endpoint:** `/request-composition`
- **Method:** `POST`
- **Description:** Request a new composition with a pending approval status (`0`).
- **Request:**
  - **Content-Type:** `application/x-www-form-urlencoded`
  - **Parameters:**
    - `content_code` (optional): Code associated with the content.
    - `composition_name` (required): Name of the composition.
    - `dosage_form` (optional): Form in which the composition is administered.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with a success message and status `0`.
  - **Error:**
    - **Status:** `400 Bad Request` or `500 Internal Server Error`
    - **Body:** JSON object with an error message.

---

### **8. Approve Composition**
- **Endpoint:** `/approve-composition`
- **Method:** `POST`
- **Description:** Approve a composition by updating its status to `1`.
- **Request:**
  - **Content-Type:** `application/json`
  - **Parameters:**
    - `composition_id` (required): ID of the composition to approve.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with a success message and status `1`.
  - **Error:**
    - **Status:** `400 Bad Request` or `500 Internal Server Error`
    - **Body:** JSON object with an error message.

---